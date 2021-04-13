
from settings import set_elasticsearch_config
# import retrieval and indexing functions so they cna be imported from a single module
from republic.elastic.republic_retrieving import *
from republic.elastic.republic_indexing import *


def initialize_es(host_type: str = 'internal', timeout: int = 10) -> Elasticsearch:
    republic_config = set_elasticsearch_config(host_type)
    es_config = republic_config['elastic_config']
    if es_config['url_prefix']:
        es_republic = Elasticsearch([{'host': es_config['host'],
                                      'port': es_config['port'],
                                      'scheme': es_config['scheme'],
                                      'url_prefix': es_config['url_prefix']}],
                                    timeout=timeout)
    else:
        es_republic = Elasticsearch([{'host': es_config['host'],
                                      'port': es_config['port'],
                                      'scheme': es_config['scheme']}],
                                    timeout=timeout)
    return es_republic


