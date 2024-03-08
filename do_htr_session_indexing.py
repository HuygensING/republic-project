import glob
import gzip
import json
import multiprocessing
import os
import pickle
import random
from collections import defaultdict

from elasticsearch.helpers import bulk
from pagexml.parser import json_to_pagexml_text_region

import republic.model.republic_document_model as rdm
from republic.elastic.republic_elasticsearch import initialize_es
# from republic.classification.line_classification import NeuralLineClassifier
from republic.model.inventory_mapping import get_inventory_by_num
from republic.parser.logical.handwritten_session_parser import get_handwritten_sessions
from republic.parser.logical.handwritten_resolution_parser import make_session_paragraphs
from republic.elastic.republic_indexing import add_timestamp, add_commit


import argparse


def make_inventory_query(inv_num):
    return {
        'bool': {
            'must': [
                {'match': {'metadata.inventory_num': inv_num}}
            ]
        }
    }


def get_inventory_session_metadata(inv_num, rep_es, index):
    query = make_inventory_query(inv_num)
    docs = [hit['_source'] for hit in rep_es.scroll_hits(rep_es.es_anno, query, index=index['metadata'], size=10)]
    docs = sorted(docs, key=lambda doc: int(doc['id'].split('-')[-1]))
    return docs


def get_inventory_session_text_regions(inv_num, rep_es, index):
    query = make_inventory_query(inv_num)
    for hit in rep_es.scroll_hits(rep_es.es_anno, query, index=index['text_regions'], size=100):
        doc = hit['_source']
        yield json_to_pagexml_text_region(doc)


def get_inventory_session_data(inv_num, rep_es):
    session_metadata_docs = get_inventory_session_metadata(inv_num, rep_es)
    for session_metadata in session_metadata_docs:
        session_trs = get_session_trs(session_metadata, rep_es)
        yield session_metadata, session_trs


def get_session_trs(session_metadata, rep_es):
    session_trs = []
    for doc_id in session_metadata['text_regions']:
        doc = rep_es.es_anno.get(index='session_text_regions', id=doc_id)
        session_tr = doc['_source']
        session_trs.append(session_tr)
    return session_trs


def read_pages(inv_num, rep_es):
    pages_file = f'./data/pages/resolution_pages/resolution_pages-inventory-{inv_num}.pcl'
    if os.path.exists(pages_file) is False:
        print('retrieving pages for inventory', inv_num)
        pages = [page for page in rep_es.retrieve_inventory_pages(inv_num)]
        if len(pages) > 0:
            with open(pages_file, 'wb') as fh:
                pickle.dump(pages, fh)
        return pages
    else:
        with open(pages_file, 'rb') as fh:
            return pickle.load(fh)


def get_inventory_num_docs(rep_es, inv_num, index):
    query = {'bool': {'must': [{'match': {'metadata.inventory_num': inv_num}}]}}
    response = rep_es.es_anno.search(index=index, query=query, size=0)
    return response['hits']['total']['value']


def make_tr_indexing_action(rep_es, tr):
    prov_url = rep_es.post_provenance(source_ids=tr.metadata['page_id'],
                                      target_ids=tr.id,
                                      source_index='pages', target_index='session_text_regions')
    tr.metadata['prov_url'] = prov_url
    add_timestamp(tr)
    add_commit(tr)
    action = {
        '_index': 'session_text_regions',
        '_id': tr.id,
        '_source': tr.json
    }
    return action


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
    pages = sorted(read_pages(inv_num, rep_es), key=lambda p: p.id)
    print(f"{len(pages)} pages returned")
    if len(pages) == 0:
        print('WARNING - skipping inventory with no pages:', inv_num)
        return None

    # print(f'loading GysBERT model for inv_num {inv_num}')
    # model_dir = './data/models/neural_line_classification/nlc_gysbert_model'
    # nlc_gysbert = NeuralLineClassifier(model_dir)

    inv_id = f'NL-HaNA_1.01.02_{inv_num}'

    total_trs = 0
    print(f'started processing inventory {inv_num}')
    try:
        actions = []
        for session_metadata, session_trs in get_handwritten_sessions(inv_id, pages):
            session_count += 1
            prov_url = rep_es.post_provenance(source_ids=session_metadata['page_ids'],
                                              target_ids=session_metadata['id'],
                                              source_index='pages', target_index='session_metadata')
            session_metadata['prov_url'] = prov_url
            rep_es.index_session_metadata(session_metadata)
            actions.extend([make_tr_indexing_action(rep_es, tr) for tr in session_trs])
            tr_count += len(session_trs)
            if len(actions) > 50:
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


def generate_paragraphs(inv_num, rep_es, index):
    print('processing inventory', inv_num)
    session_file = f'data/paragraphs/loghi/resolution-paragraphs-Loghi-{inv_num}.tsv.gz'
    # if os.path.exists(session_file):
    #     print('skipping session data for inventory', inv_num)
    #     continue
    inv_session_metas = get_inventory_session_metadata(inv_num, rep_es, index)
    if len(inv_session_metas) == 0:
        return None
    print('processing session data for inventory', inv_num)
    inv_session_trs = defaultdict(list)
    for tr in get_inventory_session_text_regions(inv_num, rep_es, index):
        inv_session_trs[tr.metadata['session_id']].append(tr)
    inv_metadata = get_inventory_by_num(inv_num)
    year = inv_metadata['year_start']

    with gzip.open(session_file, 'wt') as fh:
        for session_metadata in inv_session_metas:
            session_trs = inv_session_trs[session_metadata['id']]
            session_trs = [tr for tr in session_trs if tr.id in session_metadata['text_region_ids']]
            session_trs = sorted(session_trs, key=lambda x: session_metadata['text_region_ids'].index(x.id))
            session = rdm.Session(doc_id=session_metadata['id'], metadata=session_metadata,
                                  text_regions=session_trs)
            for para in make_session_paragraphs(session, debug=0):
                row_string = '\t'.join([str(year), para.id, para.metadata['para_type'], para.text])
                fh.write(f"{row_string}\n")


def pick_session_ids(sessions, ignore_ids, num_picks: int = 3, random_seed: int = 25662):
    session_ids = sorted(sessions.keys())
    session_ids = [session_id for session_id in session_ids if session_id not in ignore_ids]
    picked_session_ids = []
    random.seed(random_seed)
    if len(session_ids) <= num_picks:
        return [session_id for session_id in sessions]
    while len(picked_session_ids) < num_picks:
        pick = random.randint(0, len(sessions)-1)
        picked_session_ids.append(session_ids[pick])
    return picked_session_ids


def read_selected_ids():
    session_id_file = 'data/sessions/loghi/sessions-random_sample-3138-3347.session_ids.json'
    inv_selected_ids = defaultdict(list)
    with open(session_id_file, 'rt') as fh:
        session_ids = json.load(fh)
        for session_id in session_ids:
            inv = session_id[8:12]
            inv_selected_ids[inv].append(session_id)
    return session_ids


def select_paragraphs():
    random_seed = 25662
    session_random_sample_file = 'data/sessions/loghi/sessions-random_sample-3138-3347.jsonl.gz'
    selected_ids = read_selected_ids()
    fh_selected_out = gzip.open(session_random_sample_file, 'wt')
    fh_random_out = gzip.open('data/sessions/loghi/sessions-random_sample_2-3138-3347.jsonl.gz', 'wt')
    para_files = glob.glob('data/paragraphs/loghi/resolution-paragraphs-Loghi-3[123]*.tsv.gz')
    for para_file in sorted(para_files):
        with gzip.open(para_file, 'rt') as fh_in:
            sessions = defaultdict(lambda: defaultdict(list))
            for line in fh_in:
                year, para_id, text_type, text = line.strip('\n').split('\t')
                session_id = para_id.split('-para-')[0]
                sessions[session_id]['session_id'] = session_id
                sessions[session_id]['paragraphs'].append({'para_id': para_id, 'text_type': text_type, 'text': text})
                sessions[session_id]['year'] = year
            for session_id in sessions:
                if session_id in selected_ids:
                    print(f"dumping session {session_id} to selected sample")
                    fh_selected_out.write(f"{json.dumps(sessions[session_id])}\n")
            for session_id in pick_session_ids(sessions, selected_ids, num_picks=10, random_seed=random_seed):
                print(f"dumping session {session_id} to new random sample")
                #print(json.dumps(sessions[session_id]))
                fh_random_out.write(f"{json.dumps(sessions[session_id])}\n")
    fh_selected_out.close()
    fh_random_out.close()



def dummy_func(inv_num):
    print('running', inv_num)


def do_main(task, inv_start: int = None, inv_end: int = None, num_processes: int = 1):
    if inv_start is None:
        inv_start = 3096
    if inv_end is None:
        inv_end = 3348
    inv_nums = [inv_num for inv_num in range(inv_start, inv_end+1)]
    # inv_nums = [inv_num for inv_num in range(3144, 3350)]
    if task == 'index_sessions':
        if num_processes > 1:
            with multiprocessing.Pool(processes=num_processes) as pool:
                pool.map(index_inventory_sessions, inv_nums)
        else:
            for inv_num in inv_nums:
                index_inventory_sessions(inv_num)
    elif task == 'generate_paragraphs':
        index = {
            'metadata': 'session_metadata_june_2023',
            'text_regions': 'session_text_regions_june_2023'
        }
        rep_es = initialize_es(host_type="external", timeout=60)
        for inv_num in inv_nums:
            generate_paragraphs(inv_num, rep_es, index)
    elif task == 'select_paragraphs':
        select_paragraphs()
    else:
        tasks = ['index_sessions', 'generate_paragraphs', 'select_paragraphs']
        tasks_string = ', '.join([f'"{task}"' for task in tasks])
        raise ValueError(f'invalid task "{task}", must be one of {tasks_string}.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process HTR sessions.')
    parser.add_argument('task', metavar='t', type=str, nargs=1,
                        help='a task to perform')
    parser.add_argument('start', metavar='s', type=int, nargs=1,
                        help='the first inventory number of the range')
    parser.add_argument('end', metavar='e', type=int, nargs=1,
                        help='the last inventory number of the range')
    parser.add_argument('num_processes', metavar='n', type=int, nargs=1,
                        help='number of processes to run in parallel')
    args = parser.parse_args()
    print(f'task: {args.task}\tstart: {args.start}\tend: {args.end}\tnum_processes: {args.num_processes}')
    for task in args.task:
        do_main(task, args.start[0], args.end[0], args.num_processes[0])

