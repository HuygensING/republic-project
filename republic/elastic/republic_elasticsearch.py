
import settings as settings
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


def initialize_es_text_repo(timeout: int = 10):
    es_config = text_repo_es_config()
    return Elasticsearch([es_config], timeout=timeout)


def text_repo_es_config():
    es_config = {
        'host': settings.text_repo_host,
        'port': 443,
        'scheme': 'https',
        'url_prefix': settings.text_repo_url_prefix
    }
    return es_config


def set_elasticsearch_config(host_type: str = 'internal'):
    host = settings.anno_host_internal if host_type == 'internal' else settings.anno_host_external
    scheme = 'http' if host_type == 'internal' else 'https'
    port = 443 if host_type == "external" else 9200
    config = {
        'elastic_config': {
            'host': host,
            'port': port,
            'scheme': scheme,
            'url_prefix': settings.anno_url_prefix if host_type == 'external' else '',
            'url': f'{scheme}://{host}:{port}/' + f'{settings.anno_url_prefix}/' if host_type == 'external' else '',
        },
        'image_host': {
            'host_url': settings.image_host_url
        },
        'text_repo': {
            'api_url': settings.text_repo_url
        }
    }
    return config
