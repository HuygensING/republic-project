from typing import Dict, List, Union

from republic.helper.utils import get_commit_url, get_iso_utc_timestamp


def generate_es_provenance_urls(doc_ids: Union[str, List[str]], doc_index: str, es_url: str):
    """Generate provenance URLs for a list of document identifiers in a specific ES index.

    :param doc_ids: the list of document identifiers
    :param doc_index: the ES index for the documents
    :param es_url: the URL of the ES instance
    :return: the list of provenance URLs, one per document identifier
    """
    if isinstance(doc_ids, str):
        doc_ids = [doc_ids]
    return [f'{es_url}{doc_index}/_doc/{doc_id}' for doc_id in doc_ids]


def generate_es_provenance_urls_rels(doc_ids: Union[str, List[str]], doc_index: str,
                                     es_url: str, rel_type: str):
    """Generate provenance URLs for a list of document identifiers in a specific ES index.

    :param doc_ids: the list of document identifiers
    :param doc_index: the ES index for the documents
    :param es_url: the URL of the ES instance
    :param rel_type: the relationship type ('primary' or 'secondary')
    :return: the list of provenance URLs, one per document identifier
    """
    urls = generate_es_provenance_urls(doc_ids, doc_index, es_url)
    rels = [rel_type] * len(urls)
    return urls, rels


def generate_es_provenance_record(es_url: str, source_doc_index_map: List[Dict[str, any]],
                                  target_doc_index_map: List[Dict[str, any]], why: str = None):
    commit_url = get_commit_url()
    source_urls = []
    target_urls = []
    source_rels = []
    target_rels = []
    for source_type_map in source_doc_index_map:
        source_urls, source_rels = generate_es_provenance_urls_rels(source_type_map['doc_ids'],
                                                                    source_type_map['index'],
                                                                    es_url,
                                                                    source_type_map['rel'])
    for target_type_map in target_doc_index_map:
        target_urls, target_rels = generate_es_provenance_urls_rels(target_type_map['doc_ids'],
                                                                    target_type_map['index'],
                                                                    es_url,
                                                                    target_type_map['rel'])
    record = make_provenance_record(commit_url, why, source_urls, source_rels, target_urls, target_rels)
    return record


def generate_scan_provenance_record(pagexml_file: str, es_url: str, scan_id: str):
    source_urls, source_rels = [pagexml_file], ['primary']
    target_urls, target_rels = generate_es_provenance_urls_rels(scan_id, 'scans', es_url, 'primary')
    why = f'REPUBLIC CAF Pipeline deriving scan from PageXML file'
    commit_url = get_commit_url()
    return make_provenance_record(commit_url, why, source_urls, source_rels, target_urls, target_rels)


def make_provenance_data(es_config, source_ids: Union[str, List[str]], target_ids: Union[str, List[str]],
                         source_index: str, target_index: str,
                         source_es_url: str = None, target_es_url: str = None,
                         source_external_urls: Union[str, List[str]] = None, why: str = None) -> Dict[str, any]:
    """Create a provenance record based on the sources and targets, whereby the sources are the inputs and
    the targets are the outputs of a generating process.

    :param es_config: the configuration dictionary of the ES instance
    :type es_config: dict
    :param source_ids: identifiers of the sources
    :type source_ids: Union[str, List[str]]
    :param target_ids: identifiers of the targets
    :type target_ids: Union[str, List[str]]
    :param source_index: the name of the source ES index
    :type source_index: str
    :param target_index: the name of the target ES index
    :type target_index: str
    :param source_es_url: URL of ES instance for sources
    :type source_es_url: str
    :param target_es_url: URL of ES instance for targets
    :type target_es_url: str
    :param source_external_urls: URLs of external sources (not in the default ES indexes).
    :type source_external_urls: Union[str, List[str]]
    """
    if source_es_url is None:
        source_es_url = es_config['elastic_config']['url']
    if target_es_url is None:
        target_es_url = source_es_url
    if isinstance(source_ids, str):
        source_ids = [source_ids]
    if isinstance(target_ids, str):
        target_ids = [target_ids]
    if isinstance(source_external_urls, str):
        source_external_urls = [source_external_urls]
    if source_index == 'Loghi':
        source_urls = [source_id for source_id in source_ids]
    else:
        source_urls = [f'{source_es_url}{source_index}/_doc/{source_id}' for source_id in source_ids]
    if source_external_urls is not None:
        source_urls += source_external_urls
    target_urls = [f'{target_es_url}{target_index}/_doc/{target_id}' for target_id in target_ids]
    source_rels = ['primary'] * len(source_urls)
    target_rels = ['primary'] * len(target_urls)
    commit_url = get_commit_url()
    if why is None:
        why = f'REPUBLIC CAF Pipeline deriving {target_index} from {source_index}'
    return make_provenance_record(commit_url, why, source_urls, source_rels, target_urls, target_rels)


def make_provenance_record(commit_url: str, why: str, source_urls: List[str], source_rels: List[str],
                           target_urls: List[str], target_rels: List[str]):
    """Generate a provenance records according to the PROV-O standard.

    :param commit_url: the URL for the commit version of the GitHub repo used to generate targets
    :param why: a string explaining why the generation step is done
    :param source_urls: the list of URLs for the sources
    :param source_rels: the list of relations of the sources to the derivation (primary or secondary)
    :param target_urls: the list of URLs for the targets
    :param target_rels: the list of relations of the targets to the derivation (primary or secondary)
    :return:
    """
    record = {
        'who': 'orcid:0000-0002-0301-2029',
        'where': 'https://annotation.republic-caf.diginfra.org/',
        'when': get_iso_utc_timestamp(),
        'how': commit_url,
        'why': why,
        'source': source_urls,
        'source_rel': source_rels,
        'target': target_urls,
        'target_rel': target_rels
    }
    validate_provenance_record(record)
    return record


def validate_provenance_record(record: Dict[str, any]):
    """Validate the provenance record, including checks that it contains the required fields
    and that the fields have the required type. NOTE: this validation is specific to
    the REPUBLIC CAF pipeline.

    :param record: a provenance record
    :return: None
    """
    if isinstance(record, dict) is False:
        raise TypeError(f"record must be a dictionary, not {type(record)}")
    string_fields = ['who', 'where', 'when', 'how', 'why']
    list_fields = ['source', 'source_rel', 'target', 'target_rel']
    required_fields = string_fields + list_fields
    missing_fields = [field for field in required_fields if field not in record]
    if len(missing_fields) > 0:
        raise KeyError(f"provenance misses required fields {missing_fields}")
    for field in string_fields:
        if isinstance(record[field], str) is False:
            raise TypeError(f"record field '{field}' must be a string, not {type(record[field])}")
    for field in list_fields:
        if isinstance(record[field], list) is False:
            raise TypeError(f"record field '{field}' must be a list of strings, not {type(record[field])}")
        if not all(isinstance(val, str) for val in record[field]):
            raise TypeError(f"record field '{field}' must be a list of strings, not {type(record[field])}")
    for field in ['source', 'target']:
        rel_field = f"{field}_rel"
        if len(record[field]) != len(record[rel_field]):
            raise ValueError(f"record {field} does not have the same number of "
                             f"elements ({len(record[field])}) as '{rel_field}' "
                             f"({len(record[rel_field])})")
