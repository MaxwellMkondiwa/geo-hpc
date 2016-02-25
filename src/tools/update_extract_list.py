# update asdf/det extract tracker with all possible extract
# combinations available from the asdf

# --------------------------------------------------

import sys
import os

branch = sys.argv[1]

branch_dir = os.path.join(os.path.expanduser('~'), 'active', branch)

if not os.path.isdir(branch_dir):
    raise Exception('Branch directory does not exist')


config_dir = os.path.join(branch_dir, 'asdf', 'src', 'tools')
sys.path.insert(0, config_dir)

from config_utility import *

config = BranchConfig(branch=branch)


# --------------------------------------------------

import time
import pymongo


# connect to mongodb
client = pymongo.MongoClient(config.server)
asdf = client[config.asdf_db].data
extracts = client[config.det_db].extracts


# lookup all boundary datasets
boundaries = asdf.find({"type": "boundary"})

# get boundary names
bnds = [b['resources'][0]['name'] for b in boundaries]

# lookup all raster datasets
rasters = asdf.find({"type": "raster"})


items = []

# build list of dicts for all combinations of boundary names, 
# rasters names/reliabiity and respective raster extract types
for raster in rasters:

    extract_types = raster['options']['extract_types']

    items += [
        {
            'boundary': b, 
            'raster': r['name'], 
            'reliability': r['reliability'], 
            'extract_type': e
        } 
        for r in raster['resources'] 
        for e in extract_types
        for b in bnds
    ]


# check if unique extract combinations exist in tracker 
# and add if they do not
add_count = 0
for i in items:
          
    # build full doc
    ctime = int(time.time())
    
    i_full = i
    i_full["status"] = 0
    i_full["classification"] = "auto-external"
    i_full["priority"] = -1

    i_full["submit_time"] = ctime
    i_full["update_time"] = ctime


    # update/upsert and check if it exists in extracts queue
    exists = extracts.update_one(i, {'$setOnInsert': i_full}, upsert=True)
    print exists.raw_result
    if exists.raw_result['updatedExisting'] == True:
        add_count += 1


print 'Added ' + str(add_count) + ' items to extract queue (' + str(len(items)) + ' total possible).'



# example extract tracker document

# { 
#     "_id" : ObjectId("566baebf6050d566eca1f25d"), 
    
#     "boundary" : "npl_adm3", 

#     "raster" : "selv", 
#     "extract_type" : "mean", 
#     "reliability" : false,

#     "status" : 0, 
#     "classification" : "automated", 
#     "priority" : -1

#     "submit_time" : 1449897663, 
#     "update_time" : 1450383510, 
# }
