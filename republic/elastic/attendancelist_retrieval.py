from elasticsearch import Elasticsearch
import elasticsearch
from ..model.republic_attendancelist_models import TextWithMetadata
from republic.elastic.republic_retrieving import Retriever


es_api_version = elasticsearch.__version__


def make_presentielijsten(es: Elasticsearch, year: int, index: str):
    return get_presentielijsten(es=es, year=year, index=index)


def query_es(es: Elasticsearch, index, query, size=10, sort=None, aggs=None):
    if es_api_version[0] <= 7 and es_api_version[1] < 15:
        body = {
            "query": {
                query
            },
        }
        if size:
            body["size"] = size
        if sort:
            body["sort"] = sort
        if aggs:
            body["sort"] = aggs
        hits = [hit for hit in Retriever.scroll_hits(es, query, index=index, size=10)]
        # return es.search(index=index, body=body)
    else:
        hits = [hit for hit in Retriever.scroll_hits(es, query, index=index, size=10)]
        # return es.search(index=index, query=query, size=size, sort=sort, aggs=aggs)
    return hits


def get_presentielijsten(es: Elasticsearch, year: int, index: str):
    query = {
        "bool": {
            "must": [
                {"term": {'metadata.type.keyword': "attendance_list"}},
                {"term": {"metadata.session_year": year}}]
        }
    }
    size = 5000
    sort = ["_id"]
    # results = query_es(es, index, query, size=size, sort=sort)
    hits = query_es(es, index, query, size=size, sort=sort)

    presentielijsten = {}
    # for hit in results['hits']['hits']:
    for hit in hits:
        ob = hit['_source']
        mt = TextWithMetadata(ob)
        presentielijsten[mt.id] = mt
    return presentielijsten


def get_nihil_actum(es: Elasticsearch, index='republic_paragraphs'):
    query = {
        "bool": {
            "must": [
                {
                    "match": {
                        "metadata.keyword_matches.match_category": "non_meeting_date"
                    }
                }
            ],
        }
    }
    size = 5000
    sort = ["metadata.meeting_date"]
    # na_results = query_es(es, index, query, size=size, sort=sort)
    hits = query_es(es, index, query, size=size, sort=sort)
    nihil_actum = {}
    # for ob in na_results["hits"]["hits"]:
    for hit in hits:
        ob = hit['_source']
        if ob['metadata']['paragraph_id']:
            mt = TextWithMetadata(ob)
            nihil_actum[mt.id] = mt
    return nihil_actum


def simple_search(es: Elasticsearch, input_value: str):
    body = {
        "query": {
            "bool": {
                "must": [
                    {"fuzzy": {
                        "text": {
                            "value": input_value
                        }
                    }
                    }
                ],
            }
        },
        "from": 0,
        "size": 1000,
        "sort": "_score"
    }

    response = es.search(index="paragraph_index", body=body)
    results: list = [hit for hit in response['hits']['hits']]
    return results


def search_resolutions_query(text):
    """search the resolutions, not the presentielijsten (as far as they are marked as such"""
    body = {
        "query": {
            "bool": {
                "must": [
                    {"fuzzy": {"text": {"value": text}}}
                ],
                "must_not": [
                    {
                        "term": {
                            "metadata.categories": "participant_list"
                        }
                    }
                ],
            }
        },
        "from": 0,
        "size": 10000,
        "sort": [],
    }
    return body


####################
# query namenindex #
####################

'''
def get_name_from_namenindex(proposed, es: Elasticsearch):
    """get a name candidate from the namenindex.
    It does not keep count of a time frame as we only want a vote on the right name from the namenindex
    and assume that names in the namenindex tend to be uniform.
    """
    body = {
        "query": {
            "bool": {
                "must": [
                    {"fuzzy": {
                        "fullname": {
                            "value": proposed.lower()
                        }
                    }
                    }
                ],
            }
        },
        "from": 0,
        "size": 1000,
        "sort": "_score"
    }

    results = es.search(index="namenindex", body=body)
    candidate = None
    if results['hits']['total'] > 0:
        names = [r['_source']['geslachtsnaam'] for r in results['hits']['hits']]

        candidate = Counter(names).most_common(3)

    return candidate


def bulk_upload(bulkdata=[], index='attendancelist', doctype='attendancelist'):
    index = index
    indextype = doctype
    bulk_data = []
    for item in bulkdata:
        try:
            bulk_data.append({'index': {'_type': indextype,
                                        '_index': index,
                                        '_id': '%s' % item.get('id')}})
            bulk_data.append(item)
        except KeyError:
            print(item)
'''


def get_name_for_disambiguation(proposed, base_config, es: Elasticsearch, debug=False):
    """get a name candidate from the namenindex.
    It keeps count of a time frame and tries to select the most likely candidate.
    TODO make this more sophisticated
    and the time stuff syntax is apparently not good
    """
    low_date_limit = base_config['year'] - 85  # or do we have delegates that are over 85?
    high_date_limit = base_config['year'] - 20  # 20 is a very safe upper limit

    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "fuzzy": {
                            "fullname": {
                                "value": proposed.lower()
                            }
                        }
                    },
                    {
                        "range": {
                            "by": {"gt": low_date_limit,
                                   "lt": high_date_limit
                                   },
                        }
                    },
                    {
                        "range": {
                            "dy": {"lt": base_config['year'] + 50,
                                   "gt": base_config['year']
                                   },
                        }

                    }
                ],
                "should": [
                    {"match":
                         {"collection":
                              {"query": "raa",
                               "boost": 2.0
                               }
                          }
                     }
                ]
            }
        },
        "from": 0,
        "size": 1000,
        "sort": "_score"
    }

    results = es.search(index="namenindex", body=body)
    candidate = None
    if results['hits']['total'] > 0:
        names = [r['_source']['geslachtsnaam'] for r in results['hits']['hits']]
        people = [r['_source']['fullname'] for r in results['hits']['hits']]
        interjections = people = [r['_source']['intrapositie'] for r in results['hits']['hits']]
        candidate = [r for r in results['hits']['hits']]
    # think about this some more
    print('nr of candidates: {}'.format(results['hits']['total']))
    if debug == True:
        print(body)
    return candidate  # ([names, people])



