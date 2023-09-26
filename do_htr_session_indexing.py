import gzip
import multiprocessing
import os
import pickle
from collections import defaultdict

from elasticsearch.helpers import bulk
from pagexml.parser import json_to_pagexml_text_region

from republic.elastic.republic_elasticsearch import initialize_es
from republic.classification.line_classification import NeuralLineClassifier
from republic.model.inventory_mapping import get_inventory_by_num
from republic.parser.logical.handwritten_session_parser import get_sessions
from republic.parser.logical.handwritten_session_parser import make_session_paragraphs


def make_inventory_query(inv_num):
    return {
        'bool': {
            'must': [
                {'match': {'metadata.inventory_num': inv_num}}
            ]
        }
    }


def get_inventory_session_metadata(inv_num, rep_es):
    query = make_inventory_query(inv_num)
    docs = [hit['_source'] for hit in rep_es.scroll_hits(rep_es.es_anno, query, index='session_metadata', size=10)]
    docs = sorted(docs, key=lambda doc: int(doc['id'].split('-')[-1]))
    return docs


def get_inventory_session_text_regions(inv_num, rep_es):
    query = make_inventory_query(inv_num)
    for hit in rep_es.scroll_hits(rep_es.es_anno, query, index='session_text_regions', size=100):
        doc = hit['_source']
        yield json_to_pagexml_text_region(doc)


def get_inventory_session_data(inv_num, rep_es):
    session_metadata_docs = get_inventory_session_metadata(inv_num, rep_es)
    for session_metadata in session_metadata_docs:
        session_trs = get_session_trs(session_metadata, rep_es)
        yield session_metadata, session_trs


def get_session_trs(session_metadata, rep_es):
    docs = [
        {'_id': doc_id} for doc_id in session_metadata['text_regions']
    ]
    # response = rep_es.es_anno.mget(docs, index='session_text_regions')
    session_trs = []
    for doc_id in session_metadata['text_regions']:
        doc = rep_es.es_anno.get(index='session_text_regions', id=doc_id)
        session_tr = doc['_source']
        session_trs.append(session_tr)
    return session_trs


def read_pages(inv_num):
    pages_file = f'./data/pages/resolution_pages/resolution_pages-inventory-{inv_num}.pcl'
    if os.path.exists(pages_file) is False:
        return []
    with open(pages_file, 'rb') as fh:
        return pickle.load(fh)


def get_inventory_num_docs(rep_es, inv_num, index):
    query = {'bool': {'must': [{'match': {'metadata.inventory_num': inv_num}}]}}
    response = rep_es.es_anno.search(index=index, query=query, size=0)
    return response['hits']['total']['value']


def index_inventory_sessions(inv_num):
    inv_metadata = get_inventory_by_num(inv_num)
    session_count = 0
    tr_count = 0
    if inv_metadata is None or inv_metadata['content_type'] != 'resolutions':
        return None
    rep_es = initialize_es(host_type="external", timeout=60)
    # num_pages = get_inventory_num_docs(rep_es, inv_num, 'pages')
    # num_sessions = get_inventory_num_docs(rep_es, inv_num, 'session_metadata')
    # if num_sessions > 0 or num_pages == 0:
    #     return None

    print(f'loading pages for inv_num {inv_num}')
    pages = sorted(read_pages(inv_num), key=lambda p: p.id)
    if len(pages) == 0:
        print('WARNING - skipping inventory with no pages:', inv_num)
        return None

    print(f'loading GysBERT model for inv_num {inv_num}')
    model_dir = './data/models/neural_line_classification/nlc_gysbert_model'
    nlc_gysbert = NeuralLineClassifier(model_dir)

    inv_id = f'NL-HaNA_1.01.02_{inv_num}'

    total_trs = 0
    print(f'started processing inventory {inv_num}')
    try:
        actions = []
        for session_metadata, session_trs in get_sessions(inv_id, pages, nlc_gysbert):
            session_count += 1
            rep_es.index_session_metadata(session_metadata)
            for tr in session_trs:
                action = {
                    '_index': 'session_text_regions',
                    '_id': tr.id,
                    '_source': tr.json
                }
                actions.append(action)
                # rep_es.index_session_text_region(tr)
                tr_count += 1
            if len(actions) > 500:
                total_trs += len(actions)
                bulk(rep_es.es_anno, actions)
                print(f'bulk indexing {len(actions)} ({total_trs} total) text regions for inventory {inv_num}')
                actions = []
        if len(actions) > 0:
            bulk(rep_es.es_anno, actions)
            print(f'bulk indexing remaining {len(actions)} ({total_trs} total) text regions for inventory {inv_num}')
        print(f'finished processing inventory {inv_num}, with {session_count} sessions and {tr_count} trs')
    except Exception:
        print(f'Error processing inventory {inv_num}')
        raise


def generate_paragraphs(inv_num, rep_es):
    print('processing inventory', inv_num)
    session_file = f'../../data/paragraphs/loghi/resolution-paragraphs-Loghi-{inv_num}.tsv.gz'
    # if os.path.exists(session_file):
    #     print('skipping session data for inventory', inv_num)
    #     continue
    inv_session_metas = get_inventory_session_metadata(inv_num, rep_es)
    if len(inv_session_metas) == 0:
        return None
    print('processing session data for inventory', inv_num)
    inv_session_trs = defaultdict(list)
    for tr in get_inventory_session_text_regions(inv_num, rep_es):
        inv_session_trs[tr.metadata['session_id']].append(tr)
    inv_metadata = get_inventory_by_num(inv_num)
    year = inv_metadata['year_start']

    with gzip.open(session_file, 'wt') as fh:
        for session_metadata in inv_session_metas:
            session_trs = inv_session_trs[session_metadata['id']]
            session_trs = sorted(session_trs, key=lambda x: session_metadata['text_regions'].index(x.id))
            for para in make_session_paragraphs(session_metadata, session_trs, debug=0):
                row_string = '\t'.join([str(year), para.id, para.metadata['para_type'], para.text])
                fh.write(f"{row_string}\n")


def dummy_func(inv_num):
    print('running', inv_num)


def do_main(task):
    inv_nums = [inv_num for inv_num in range(3118, 3350)]
    if task == 'index_sessions':
        num_processes = 6
        with multiprocessing.Pool(processes=num_processes) as pool:
            pool.map(index_inventory_sessions, inv_nums)
    elif task == 'generate_paragraphs':
        rep_es = initialize_es(host_type="external", timeout=60)
        for inv_num in inv_nums:
            generate_paragraphs(inv_num, rep_es)


if __name__ == "__main__":
    do_main()
