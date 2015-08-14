from mpi4py import MPI
import subprocess as sp
import sys
import os

runscript = sys.argv[1]


comm = MPI.COMM_WORLD

size = comm.Get_size()
rank = comm.Get_rank()

# base path where year/day directories for processed data are located
path_base = "/sciclone/data20/aiddata/REU/data/gimms.gsfc.nasa.gov/MODIS/std/GMOD09Q1/tif/NDVI/"

# list of years to ignore
ignore = ['2006','2007','2008','2009']


# list of all [year, day] combos
qlist = []


# get years
years = [name for name in os.listdir(path_base) if os.path.isdir(os.path.join(path_base, name)) and name not in ignore]
years.sort()
# use limited years for testing 
# years = ['2002','2003','2004']


for year in years:

	# get days for year
	path_year = path_base + year
	days = [name for name in os.listdir(path_year) if os.path.isdir(os.path.join(path_year, name))]
	days.sort()
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
	# print "Rscript "+runscript+" "+qlist[c][0]+" "+qlist[c][1]+" "+qlist[c][2]

	try:
		cmd = "Rscript "+runscript+" "+qlist[c][0]+" "+qlist[c][1]+" "+qlist[c][2]
		sts = sp.check_output(cmd, stderr=sp.STDOUT, shell=True)
		print sts

	except sp.CalledProcessError as sts_err:                                                                                                   
	    print ">> subprocess error code:", sts_err.returncode, '\n', sts_err.output

	c += size


comm.Barrier()
