#!/bin/tcsh
#PBS -N ad:sg-mcr
#PBS -l nodes=2:c11:ppn=8
#PBS -l walltime=04:00:00
#PBS -j oe

cd $PBS_O_WORKDIR
mvp2run -m cyclic python-mpi ./runscript.py nepal NPL 0.5 10
