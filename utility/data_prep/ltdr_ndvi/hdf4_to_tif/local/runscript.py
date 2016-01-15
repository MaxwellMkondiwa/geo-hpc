# for use with NDVI product from LTDR raw dataset (AVH13C1)


# example LTDR product file names

# AVH02C1.A1981299.N07.004.2013228133954.hdf
# AVH09C1.A1981211.N07.004.2013228083053.hdf
# AVH13C1.A1981181.N07.004.2013227210959.hdf

# split file name by "."
# eg: 
# 
# full file name - "AVH13C1.A1981181.N07.004.2013227210959.hdf"
# 
# 0		product code	 	AVH13C1
# 1 	date of image		A1981181
# 2 	sensor code			N07
# 3 	misc 			 	004
# 4 	processed date 		2013227210959
# 5 	extension 			hdf

# ndvi product code is AVH13C1


import subprocess as sp
import sys
import os


runscript = "/home/userz/kfw/ltdr_prep/local/ltdr_ndvi_prep.sh"



# base path where data is located
# data downloaded using wget (same wget call can be used to download new data)
# wget -r -c -N --retr-symlinks=yes ftp://ltdr.nascom.nasa.gov/allData/Ver4/
path_base = "/home/userz/globus-data/raw/ltdr.nascom.nasa.gov/allData/Ver4"


# reference object used to eliminate duplicate year / day combos
# when overlaps between sensors exists, always use data from newer sensor
ref = {}

# list of all [year, day] combos

sensor_accept = ["N18"]

# get sensors
sensors = [name for name in os.listdir(path_base) if os.path.isdir(os.path.join(path_base, name)) and name in sensor_accept]
sensors.sort()

# use limited sensors for testing 
# sensors = ['2001']


for sensor in sensors:

	# get years for sensors
	path_sensor = path_base +"/"+ sensor
	years = [name for name in os.listdir(path_sensor) if os.path.isdir(os.path.join(path_sensor, name))]
	years.sort()

	for year in years:

		if not year in ref:
			ref[year] = {}


		# get days for year
		path_year = path_sensor +"/"+ year
		filenames = [name for name in os.listdir(path_year) if not os.path.isdir(os.path.join(path_year, name)) and name.endswith(".hdf") and name.split(".")[0] == "AVH13C1"]
		filenames.sort()

		for filename in filenames:

			filename = filename[:-4]
			day = filename.split(".")[1][5:]

			if not day in ref[year] or int(sensor[1:]) > int(ref[year][day][0][1:]):
				# print "\n" + str(year) +" "+ str(day) +" "+ str(sensor) +" "+ str(filename)
				ref[year][day] = [sensor, filename]



# list final [sensor, year, day] combos from reference object
# qlist = [ref[year][day] + [year, day] for day in ref[year] for year in ref if year in ref and day in ref[year]]

qlist = []
for year in ref:
	for day in ref[year]:
 		qlist.append(ref[year][day] + [year, day]) 
 		# print qlist

for c in range(len(qlist)):

	try:
		cmd = "bash "+runscript+" "+qlist[c][0]+" "+qlist[c][1]+" "+qlist[c][2]+" "+qlist[c][3]
		# print cmd

		sts = sp.check_output(cmd, stderr=sp.STDOUT, shell=True)
		print sts

	except sp.CalledProcessError as sts_err:                                                                                                   
	    print "subprocess error code", sts_err.returncode, sts_err.output

