import copy

import settings as settings

import elasticsearch
from elasticsearch import Elasticsearch

# import retrieval and indexing functions so they cna be imported from a single module
from republic.config.republic_config import base_config
from republic.elastic.republic_retrieving import Retriever
from republic.elastic.republic_indexing import Indexer


def initialize_es_anno(host_type: str = 'internal', timeout: int = 10) -> Elasticsearch:
    api_config = set_elasticsearch_config(host_type)
    es_config = api_config['elastic_config']
    if es_config['url_prefix']:
        es_anno = Elasticsearch([{'host': es_config['host'],
                                  'port': es_config['port'],
                                  'scheme': es_config['scheme'],
                                  'url_prefix': es_config['url_prefix']}],
                                timeout=timeout)
    else:
        es_anno = Elasticsearch([{'host': es_config['host'],
                                  'port': es_config['port'],
                                  'scheme': es_config['scheme']}],
                                timeout=timeout)
    return es_anno


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


class RepublicElasticsearch(Retriever, Indexer):

    def __init__(self, es_anno: Elasticsearch, es_text: Elasticsearch, config: dict):
        super().__init__(es_anno, es_text, config)


def initialize_es(host_type: str = "external", timeout: int = 10,
                  config: dict = None, commit_version: str = None) -> RepublicElasticsearch:
    es_anno = initialize_es_anno(host_type=host_type, timeout=timeout)
    es_text = initialize_es_text_repo(timeout=timeout)
    if config is None:
        config = copy.deepcopy(base_config)
    config["commit_version"] = commit_version
    if hasattr(settings, "prov_host_url"):
        config["prov_host_url"] = settings.prov_host_url
    else:
        print("settings.py is missing a prov_host_url variable. Consider adding "
              "a line 'prov_host_url = None' to your settings.py")
        config["prov_host_url"] = None
    config["es_api_version"] = elasticsearch.__version__
    return RepublicElasticsearch(es_anno, es_text, config)


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
