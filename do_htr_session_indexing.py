import multiprocessing
import os
import pickle

from elasticsearch.helpers import bulk

from republic.elastic.republic_elasticsearch import initialize_es
from republic.classification.line_classification import NeuralLineClassifier
from republic.model.inventory_mapping import get_inventory_by_num
from republic.parser.logical.handwritten_session_parser import get_sessions


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
    except Exception as err:
        print(f'Error processing inventory {inv_num}')
        raise


def dummy_func(inv_num):
    print('running', inv_num)


def do_main():
    inv_nums = [inv_num for inv_num in range(3118, 3350)]
    num_processes = 6
    with multiprocessing.Pool(processes=num_processes) as pool:
        pool.map(index_inventory_sessions, inv_nums)


if __name__ == "__main__":
    do_main()
