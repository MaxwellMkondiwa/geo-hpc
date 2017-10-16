#!/bin/bash

# automated script called by cron_wrapper.sh
#
# builds jobs for specified tasks
#
# required input:
#   branch
#   timestamp
#   task - which job to build
#
# only allows 1 job of each task type to run at a time
# utilizes qstat grep to search for standardized job name to
# determine if job is already running
#
# job name format: geo-<short_name>-<branch>


branch=$1

timestamp=$2

task=$3

jobtime=$(date +%H%M%S)

branch_dir="/sciclone/aiddata10/geo/${branch}"
src="${branch_dir}/source"

case "$task" in

    error_check)
        short_name=ec
        ppn=1
        cmd="python ${src}/geo-hpc/tasks/check_errors.py ${branch}"
        ;;

    update_trackers)
        short_name=upt
        ppn=16
        cmd="mpirun --mca mpi_warn_on_fork 0 --map-by node -np 16 python-mpi ${src}/geo-hpc/tasks/update_trackers.py ${branch}"
        ;;

    update_extract)
        short_name=upe
        ppn=16
        cmd="mpirun --mca mpi_warn_on_fork 0 --map-by node -np 16 python-mpi ${src}/geo-hpc/tasks/update_extract_queue.py ${branch}"
        ;;

    update_msr)
        short_name=upm
        ppn=1
        cmd="mpirun --mca mpi_warn_on_fork 0 -np 1 python-mpi ${src}/geo-hpc/tasks/update_msr_queue.py ${branch}"
        ;;

    det)
        short_name=det
        ppn=1
        cmd="python ${src}/geo-hpc/tasks/geoquery_request_processing.py ${branch}"
        ;;

    *)  echo "Invalid build_db_updates_job task.";
        exit 1 ;;
esac


# check if job needs to be run
qstat=$(/usr/local/torque-6.0.2/bin/qstat -nu $USER)

if echo "$qstat" | grep -q 'geo-'"$short_name"'-'"$branch"; then

    printf "%0.s-" {1..40}
    echo -e "\n"

    echo [$(date) \("$timestamp"."$jobtime"\)] Existing job found
    echo "$qstat"
    echo -e "\n"

else

    printf "%0.s-" {1..80}
    echo -e "\n"


    job_dir="$branch_dir"/log/"$task"/jobs
    mkdir -p $job_dir

    shopt -s nullglob
    for i in "$job_dir"/*.job; do
        cat "$i"
        rm "$i"

        printf "%0.s-" {1..80}
        echo -e "\n"
    done

    echo [$(date) \("$timestamp"."$jobtime"\)] No existing job found.
    echo "Building job..."

    job_path=$(mktemp)


# NOTE: just leave this heredoc unindented
#   sublime text is set to indent with spaces
#   heredocs can only be indented with true tabs
#   (can use `cat <<- EOF` to strip leading tabs )


cat <<EOF >> "$job_path"
#!/bin/tcsh
#PBS -N geo-$short_name-$branch
#PBS -l nodes=1:c18c:ppn=$ppn
#PBS -l walltime=48:00:00
#PBS -j oe
#PBS -o $branch_dir/log/$task/jobs/$timestamp.$jobtime.$task.job
#PBS -V

echo "\n"
date
echo "\n"

echo Timestamp: $timestamp
echo Job: "\$PBS_JOBID"
echo "\n"

$cmd

echo "\n"
date
echo "\nDone \n"

EOF

    # cd "$branch_dir"/log/"$task"/jobs
    /usr/local/torque-6.0.2/bin/qsub "$job_path"

    echo "Running job..."
    echo -e "\n"

    # for debug
    # cp "$job_path" ${HOME}

    rm "$job_path"

fi
