#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  6 10:49:09 2019

@author: rikhoekstra
"""

# # To Elastic Search


import os
import datetime
import json
import re
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError


es = Elasticsearch(timeout=30, max_retries=10, retry_on_timeout=True)

basedir = '.'




# create mapping in index (the index should already exist)


mapping = {
            "naam": {
                    "properties":{
                        'geslachtsnaam': {"type":"text"},
                        'fullname': {"type":"text"},
                        'birth': {"type":"text"},
                        'death': {"type":"text"},
                        'by': {"type":"integer"},
                        'dy': {"type":"integer"},
                        'bp': {"type":"text"},
                        'dp': {"type":"text"},
                        'biography': {"type":"text"},
                        'reference': {"type":"text"}
                        }
                    }
                }



def main(index="namenindex",
         mapping=mapping,
         doc_type="naam",
         basedir=basedir,
         srcfile='ni_nw.json',
         update=False):
    """main handler. with update just update the index """


    index =index
    if update == False: # only delete index if update is False
        if es.indices.exists(index):
            es.indices.delete(index)
        es.indices.create(index)


    request_body=mapping
    es.indices.put_mapping(index = index,
                           doc_type=doc_type,
                           body=request_body)

    # check mapping
    mapping = es.indices.get_mapping(index = index)
    print('working with mapping: {}'.format(mapping))



    jsonfile = open(os.path.join(basedir,srcfile))
    data_dict = json.load(jsonfile)
    jsonfile.close()

    bulk_data = []

    for item in enumerate(data_dict): # no idnrs assumed
        try:
            id = item[0]
            bulk_data.append({'index':{'_type':'naam',
                                       '_index':index,
                                       '_id':'%s' % id}})
            bulk_data.append(item[1])
        except KeyError:
            print (item)


    es.bulk(index=index, body=bulk_data, refresh=True)


if __name__ ==  '__main__':
    """this should change to using optionparser
    """
    main()
