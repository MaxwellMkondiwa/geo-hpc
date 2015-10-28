# accepts request object and checks if all extracts have been processed (return boolean)

import os
import errno
import time
import json

import hashlib

import pymongo
import pandas as pd 
import geopandas as gpd



class cache():
    
    def __init__(self):
        # connect to mongodb
        self.client = pymongo.MongoClient()
        self.db = self.client.det

        # extract queue
        self.c_extracts = self.db.extracts
        
        # msr tracker
        self.c_msr = self.db.msr        

        self.extract_options = json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/extract_options.json', 'r'))

        self.merge_lists = {}

        self.msr_resolution = 0.05
        self.msr_version = 0.1


    # creates directories
    def make_dir(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise


    def json_sha1_hash(self, hash_obj):
        hash_json = json.dumps(hash_obj, sort_keys = True, ensure_ascii = False, separators=(',', ':'))
        hash_builder = hashlib.sha1()
        hash_builder.update(hash_json)
        hash_sha1 = hash_builder.hexdigest()
        return hash_sha1


    # check entire request object for cache
    def check_request(self, rid, request, extract=False):
        print "check_request"

        self.merge_lists[rid] = []
        extract_count = 0
        msr_count = 0

        msr_field_id = 1

        for name in sorted(request['d1_data'].keys()):
            data = request['d1_data'][name]  

        # for name, data in request['d1_data'].iteritems():  

            print name

            data['resolution'] = self.msr_resolution
            data['version'] = self.msr_version

            # get hash
            data_hash = self.json_sha1_hash(data)

            msr_extract_type = "sum"
            msr_extract_output = "/sciclone/aiddata10/REU/extracts/" + request["boundary"]["name"] +"/cache/"+ data['dataset'] +"/"+ msr_extract_type +"/"+ data_hash +"_"+self.extract_options[msr_extract_type] +".csv"    

            # check if msr exists in tracker and is completed
            msr_exists, msr_completed = self.msr_exists(data['dataset'], data_hash)

            if msr_completed:
                
                # check if extract for msr exists in queue and is completed  
                extract_exists, extract_completed = self.extract_exists(request["boundary"]["name"], data['dataset']+"_"+data_hash, msr_extract_type, True, msr_extract_output)
                
                if not extract_completed:
                    extract_count += 1

                    if not extract_exists:
                        # add to extract queue
                        self.add_to_extract_queue(request["boundary"]["name"], data['dataset']+"_"+data_hash, True, msr_extract_type, "msr")

            else:

                msr_count += 1
                extract_count += 1

                if not msr_exists:
                    # add to msr tracker
                    self.add_to_msr_tracker(data, data_hash)


            # add to merge list
            self.merge_lists[rid].append(('d1_data', msr_extract_output, msr_field_id))
            self.merge_lists[rid].append(('d1_data', msr_extract_output[:-5]+"r.csv", msr_field_id))

            msr_field_id += 1


        for name, data in request["d2_data"].iteritems():
            print name

            for i in data["files"]:

                df_name = i["name"]
                raster_path = data["base"] +"/"+ i["path"]
                is_reliability_raster = i["reliability"]

                for extract_type in data["options"]["extract_types"]:

                    # core basename for output file 
                    # does not include file type identifier (...e.ext for extracts and ...r.ext for reliability) or file extension
                    if data["temporal_type"] == "None":
                        output_name = df_name + "_"
                    else:
                        output_name = df_name

                    # output file string without file type identifier or file extension
                    base_output = "/sciclone/aiddata10/REU/extracts/" + request["boundary"]["name"] +"/cache/"+ data["name"] +"/"+ extract_type +"/"+ output_name
                    extract_output = base_output + self.extract_options[extract_type] + ".csv"
                    
                    # check if extract exists in queue and is completed
                    extract_exists, extract_completed = self.extract_exists(request["boundary"]["name"], df_name, extract_type, is_reliability_raster, extract_output)

                    # incremenet count if extract is not completed (whether it exists in queue or not)
                    if not extract_completed:
                        extract_count += 1

                        # add to extract queue if it does not already exist in queue
                        if not extract_exists:
                            self.add_to_extract_queue(request['boundary']['name'], i['name'], is_reliability_raster, extract_type, "external")


                    # add to merge list
                    self.merge_lists[rid].append(('d2_data', extract_output, None))
                    if is_reliability_raster:
                        self.merge_lists[rid].append(('d2_data', extract_output[:-5]+"r.csv", None))


        return 1, extract_count, msr_count


    # add extract item to det->extracts mongodb collection    
    def add_to_extract_queue(self, boundary, raster, reliability, extract_type, classification):
        print "add_to_extract_queue"
        
        ctime = int(time.time())     

        insert = {
            'raster': raster,
            'boundary': boundary,
            'reliability': reliability,
            'extract_type': extract_type,
            'classification': classification,

            'status': 0,
            'priority': 0,
            'submit_time': ctime,
            'update_time': ctime       
        }

        self.c_extracts.insert(insert)


    # add msr item to det->msr mongodb collection
    def add_to_msr_tracker(self, selection, msr_hash):
        print "add_to_msr_tracker"
        
        ctime = int(time.time())     

        insert = {
            'hash': msr_hash,

            'dataset': selection['dataset'],
            'options': selection,
            # 'resolution': 0.05,

            'job': [],
            'status': 0,
            'priority': 0,
            'submit_time': ctime,
            'update_time': ctime
        }

        self.c_msr.insert(insert)


    # 1) check if extract exists in extract queue
    #    run redundancy check on actual extract file and delete extract queue entry if file is missing
    #    also check for reliability calc if field is specified
    # 2) check if extract is completed, waiting to be run, or encountered an error
    def extract_exists(self, boundary, raster, extract_type, reliability, csv_path):
        print "exists_in_extract_queue"
        
        check_data = {"boundary": boundary, "raster": raster, "extract_type": extract_type, "reliability": reliability}

        # check db
        search = self.c_extracts.find(check_data)

        db_exists = search.count() > 0

        valid_exists = False
        valid_completed = False

        if db_exists:
            print search[0] 

            if search[0]['status'] == 0:
                valid_exists = True

            elif search[0]['status'] == 1:
                # check file
                extract_exists = os.path.isfile(csv_path)

                reliability_path = csv_path[:-5] + "r.csv"

                if extract_exists and (not reliability or (reliability and os.path.isfile(reliability_path))):
                    valid_exists = True
                    valid_completed = True

                else:
                    # remove from db
                    self.c_extracts.delete_one(check_data)

            else:
                valid_exists = True
                valid_completed = "Error"


        return valid_exists, valid_completed


    # 1) check if msr exists in msr tracker
    #    run redundancy check on actual msr raster file and delete msr tracker entry if file is missing
    # 2) check if msr is completed, waiting to be run, or encountered an error
    def msr_exists(self, dataset_name, msr_hash):
        print "exists_in_msr_tracker"
        
        check_data = {"dataset": dataset_name, "hash": msr_hash}

        # check db
        search = self.c_msr.find(check_data)

        db_exists = search.count() > 0

        valid_exists = False
        valid_completed = False

        if db_exists:

            if search[0]['status'] == 0:
                valid_exists = True

            elif search[0]['status'] == 1:
                # check file
                raster_path = '/sciclone/aiddata10/REU/data/rasters/internal/msr/' + dataset_name +'/'+ msr_hash +'/raster.asc'
                msr_exists = os.path.isfile(raster_path)

                if msr_exists:
                    valid_exists = True
                    valid_completed = True

                else:
                    # remove from db
                    self.c_msr.delete_one(check_data)

            else:
                valid_exists = True
                valid_completed = "Error"


        return valid_exists, valid_completed



# ---------------------------------------------------------------------------



    # merge extracts when all are completed
    def merge(self, rid, request):
        print "merge"

        # # generate list of csv files to merge (including relability calcs)
        # csv_merge_list = []
        # for item in self.merge_lists[rid]:
        #     csv_merge_list.append(item['output'])
        #     if item['reliability']:
        #         csv_merge_list.append(item['output'][:-5]+"r.csv")


        merged_df = 0

        # used to track dynamically generated field names 
        # so corresponding extract and reliability have consistent names
        merge_log = {}

        # created merged dataframe from results
    # try:

        # for each result file that should exist for request (extracts and reliability)
        for merge_item in self.merge_lists[rid]:
            merge_class, result_csv, dynamic_merge_count = merge_item

            # make sure file exists
            if os.path.isfile(result_csv):

                if merge_class == 'd2_data':
                    # get field name from file
                    result_field =  os.path.splitext(os.path.basename(result_csv))[0]

                elif merge_class == 'd1_data':

                    csv_basename = os.path.splitext(os.path.basename(result_csv))[0]
                    
                    merge_log_name = csv_basename[:-2]

                    if not merge_log_name in merge_log.keys():

                        dynamic_merge_string = '{0:03d}'.format(dynamic_merge_count)

                        merge_log[merge_log_name] = 'ad_msr' + dynamic_merge_string


                    result_field = merge_log[merge_log_name] + csv_basename[-1:]


                # load csv into dataframe
                result_df = pd.read_csv(result_csv, quotechar='\"', na_values='', keep_default_na=False)

                # check if merged df exists
                if not isinstance(merged_df, pd.DataFrame):
                    # if merged df does not exists initialize it 
                    # init merged df using full csv                    
                    merged_df = result_df.copy(deep=True)
                    # change extract column name to file name
                    merged_df.rename(columns={"ad_extract": result_field}, inplace=True)

                else:
                    # if merge df exists add data to it
                    # add only extract column to merged df
                    # with column name = new extract file name
                    merged_df[result_field] = result_df["ad_extract"]

    # except:
        # return False, "error building merged dataframe"


        # output merged dataframe to csv
    # try:
        merged_output = "/sciclone/aiddata10/REU/det/results/"+rid+"/results.csv"

        # generate output folder for merged df using request id
        self.make_dir(os.path.dirname(merged_output))

        # write merged df to csv
        merged_df.to_csv(merged_output, index=False)
        
        return True, None
    
    # except:
    #     return False, "error writing merged dataframe"           




# ---------------------------------------------------------------------------



    # # generate merge list for request
    # def generate_merge_list(self, request):
    #     print "generate_merge_list"

    #     tmp_merge_list =  []

    #     boundary_path = request['boundary']['path']


    #     for name, data in request['d1_data'].iteritems():                   
    #         print name

    #         msr_raster_path = ''
    #         msr_extract_output = ''
    #         msr_field = ''

    #         tmp_merge_item = {
    #             'boundary': boundary_path,
    #             'raster': msr_raster_path,
    #             'extract': 'sum',
    #             'reliability': True,
    #             'field': msr_field,
    #             'output': msr_extract_output,
    #             'type': 'raster',
    #             'source': 'd1_data'
    #         }
            
    #         tmp_merge_list.append(tmp_merge_item)


    #     for name, data in request["d2_data"].iteritems():
    #         print name

    #         for i in data["files"]:

    #             df_name = i["name"]
    #             raster_path = data["base"] +"/"+ i["path"]
    #             is_reliability_raster = i["reliability"]

    #             for extract_type in data["options"]["extract_types"]:

    #                 # core basename for output file 
    #                 # does not include file type identifier (...e.ext for extracts and ...r.ext for reliability) or file extension
    #                 if data["temporal_type"] == "None":
    #                     output_name = df_name + "_"
    #                 else:
    #                     output_name = df_name

    #                 # output file string without file type identifier or file extension
    #                 base_output = "/sciclone/aiddata10/REU/extracts/" + request["boundary"]["name"] +"/cache/"+ data["name"] +"/"+ extract_type +"/"+ output_name
    #                 extract_output = base_output + self.extract_options[extract_type] + ".csv"
                    

    #                 tmp_merge_item = {
    #                     'boundary': boundary_path,
    #                     'raster': raster_path,
    #                     'extract': extract_type,
    #                     'reliability': is_reliability_raster,
    #                     'field': os.path.basename(extract_output),
    #                     'output': extract_output,
    #                     'type': 'raster',
    #                     'source': 'd2_data'
    #                 }

    #                 tmp_merge_list.append(tmp_merge_item)


    #     self.merge_list = tmp_merge_list

    #     return len(merge_list)






