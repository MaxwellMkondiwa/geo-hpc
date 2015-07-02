from mpi4py import MPI
import subprocess as sp
import sys
import os

runscript = sys.argv[1]


# --------------------------------------------------

# project name (must match folder in /sciclone/aiddata10/REU/projects)
project_name = sys.argv[2] # "kfw"

# shapefile file name (no path or extension)
shape_name = sys.argv[3] # "terra_indegenousMatched"

atap_type = sys.argv[4] # "terrestrial_air_temperature"
# atap_type = "terrestrial_precipitation"

# --------------------------------------------------


comm = MPI.COMM_WORLD
size = comm.Get_size()
rank = comm.Get_rank()


# base path where year/day directories for processed data are located
path_base = "/sciclone/aiddata10/REU/data/" + atap_type + "/"

# list of years to ignore
ignore = []

# list of all [year, day] combos
qlist = []

# get years
years = [name for name in os.listdir(path_base) if os.path.isdir(os.path.join(path_base, name)) and name not in ignore]

# use limited years for testing 
# years = ['2002','2003','2004']


for year in years:

	# get days for year
	path_year = path_base + year
	days = [name for name in os.listdir(path_year) if os.path.isdir(os.path.join(path_year, name))]

	# use limited days for testing 
	# days = ['001','009']
	# days = ['001','009','017','025']
	# days = ['001','009','017','025','033','041']
	# days = ['001','009','017','025','033','041','049','057']
	# days = ['065','073','081','089','097','105','113','121']
	# days = ['001','009','017','025','033','041','049','057','065','073','081','089','097','105','113','121']


	for day in days:

		path_day = path_year + "/" + day
		flist = [name for name in os.listdir(path_day) if not os.path.isdir(os.path.join(path_day, name)) and name.endswith('.tif')]
		qlist += [[year,day,name] for name in flist if len(flist) == 1]


c = rank
while c < len(qlist):

	try:
		cmd = "Rscript "+runscript+" "+qlist[c][0]+" "+qlist[c][1]+" "+qlist[c][2]+" "+atap_type+" "+project_name+" "+shape_name
		sts = sp.check_output(cmd, stderr=sp.STDOUT, shell=True)
		print sts

	except sp.CalledProcessError as sts_err:                                                                                                   
	    print ">> subprocess error code:", sts_err.returncode, '\n', sts_err.output

	c += size


comm.Barrier()
