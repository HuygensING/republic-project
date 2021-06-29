#from ..config.republic_config import base_config
#from elasticsearch import Elasticsearch
from collections import Counter
from ..elastic.republic_elasticsearch import initialize_es
from ..model.republic_attendancelist_models import TextWithMetadata

es_republic = initialize_es(host_type="external", timeout=60)
def make_presentielijsten(es=es_republic, year='0', index='session_text'):
    return get_presentielijsten(year=year, index=index, es=es_republic)

def get_presentielijsten(year: str = '0', index: str = 'session_text', es: object =None):
    prs_body = {"query":
                  {"bool":
                    {
                        "must": [
                         {"term":
                      {"annotations.metadata.type.keyword":
                         "attendance_list"}},
                      {"term": {"metadata.session_year":
                         year}}]
                    }
                  },
                  "size": 5000,
                  "sort": ["_id"],
                }

    presentielijsten = {}
    results = es.search(index=index, body=prs_body)
    for ob in results['hits']['hits']:
      try:
        mt = TextWithMetadata(ob)
        presentielijsten[mt.id] = mt
      except AttributeError:
        print(ob)
    return presentielijsten


def get_nihil_actum(es=es_republic, index='republic_paragraphs'):
  na_body = {"query": {
    "bool": {
      "must": [
        {
          "match": {
            "metadata.keyword_matches.match_category": "non_meeting_date"
          }
        }
      ],

    }
  },
    "size": 5000,
    "sort": ["metadata.meeting_date"],
  }

  na_results = es.search(index=index, body=na_body)
  nihil_actum = {}
  for ob in na_results["hits"]["hits"]:
    if ob['_source']['metadata']['paragraph_id']:
      mt = TextWithMetadata(ob)
      nihil_actum[mt.id] = mt
  return nihil_actum


# for n in nihil_actum.keys():
#     nad = nihil_actum[n]
#     print(nad.get_meeting_date(), ": ", n)


def simple_search(es, input):
    body = {
      "query": {
        "bool": {
          "must": [
            {"fuzzy": {
              "text": {
                "value": input
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
  
    results: list = es.search(index="paragraph_index", body=body)
    return results


def search_resolutions_query(text):
    """search the resolutions, not the presentielijsten (as far as they are marked as such"""
    body = {
      "query": {
        "bool": {
          "must":
            [{
              "fuzzy":
                {"text":
                   {"value": text
                    }
                 }
            }
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
    #return results
    


####################
# query namenindex #
####################

def get_name_from_namenindex(proposed, es=es_republic):
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


def get_name_for_disambiguation(proposed, base_config, es=es_republic, debug=False):
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



