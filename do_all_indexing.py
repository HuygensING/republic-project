import tarfile
import datetime
import logging
import xml
from collections import defaultdict

from elasticsearch.exceptions import ElasticsearchException

from republic.elastic.republic_elasticsearch import initialize_es
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser

rep_es = initialize_es(host_type="internal", timeout=60)


def index_scan(inv_file, file_content, inv_metadata, inv_file_count: int = 0):
        try:
            scan = pagexml_parser.get_scan_pagexml(inv_file, pagexml_data=file_content, inv_metadata=inv_metadata)
            print(f"inv {scan.metadata['inventory_num']}, scan {inv_file_count} - indexing scan {scan.id} with {scan.stats['words']} words")
            prov_url = rep_es.post_provenance([inv_file], [scan.id], 'Loghi', 'scans')
            scan.metadata['provenance_url'] = prov_url
            rep_es.index_scan(scan)
        except (xml.parsers.expat.ExpatError, ValueError, IndexError, KeyError, TypeError, ElasticsearchException, AttributeError) as err:
            print(f'Error parsing file {inv_file} - {err}')
            logging.error(f'Error parsing file {inv_file} - {err}')
            pass


def do_htr_handwritten():
    all_file = 'data/pagexml/loghi-htr.tgz'
    file_count = 0
    inv_metadata = None
    with tarfile.open(all_file, 'r:gz') as fh:
        print('opened tarfile')
        for file_info in fh:
            if file_info.isdir():
                print('Dir:', file_info.name)
                logging.info(f'extracting scans from dir {file_info.name}')
                inv_num = int(file_info.name)
                inv_metadata = rep_es.retrieve_inventory_metadata(inv_num)
                continue
            elif file_info.name.endswith('.xml') is False:
                logging.info(f'skipping non-XML file {file_info.name}')
                continue
            file_reader = fh.extractfile(file_info)
            file_content = file_reader.read()
            index_scan(file_info.name, file_content, inv_metadata)
            file_count += 1
            if file_count % 1000 == 0:
                print(file_count, 'pagexml files processed')
                logging.info(f'{file_count} pagexml files processed')
    print('Finished!')


def do_htr_printed():
    all_file = 'data/pagexml/pagexml-loghi_htr-2022-invs_3760-3864.tgz'
    file_count = 0
    inv_file_count = defaultdict(int)
    inv_metadata = None
    do_index = False
    with tarfile.open(all_file, 'r:gz') as fh:
        print('opened tarfile')
        for file_info in fh:
            if file_info.isdir():
                print('Dir:', file_info.name)
                logging.info(f'extracting scans from dir {file_info.name}')
                inv_num = int(file_info.name)
                inv_metadata = rep_es.retrieve_inventory_metadata(inv_num)
                continue
            elif file_info.name.endswith('.xml') is False:
                logging.info(f'skipping non-XML file {file_info.name}')
                continue
            elif file_info.name.startswith(f"{inv_num}/._"):
                continue
            # print('file_content:', file_content)
            # print('file_info.name:', file_info.name)
            # print('inv_metadata:', inv_metadata)
            # print('inv_num:', inv_num, '\tdo_index:', do_index)
            inv_file_count[inv_num] += 1
            if inv_num == 3848:
                do_index = True
            if do_index is True:
                file_reader = fh.extractfile(file_info)
                file_content = file_reader.read()
                index_scan(file_info.name, file_content, inv_metadata, inv_file_count[inv_num])
            file_count += 1
            if file_count % 1000 == 0:
                print(file_count, 'pagexml files processed')
                logging.info(f'{file_count} pagexml files processed')
    print('Finished!')


def main():
    # do_htr_handwritten()
    do_htr_printed()


if __name__ == "__main__":
    today = datetime.date.today().isoformat()
    import logging.config
    logging.config.dictConfig({
       'version': 1,
        # Other configs ...
        'filename': f'indexing-all-HTR-{today}.log',
        'disable_existing_loggers': True
    })
    # logger = logging.getLogger('all_htr_indexer')
    # logger.setLevel(logging.DEBUG)
    for name, logger in logging.root.manager.loggerDict.items():
        print(name, logger.disabled)
        if 'elasticsearch' in name:
            logger.disabled=True
    logging.basicConfig(format='%(asctime)s %(message)s',
                        filename=f'indexing-all-HTR-{today}.log',
                        #encoding='utf-8',
                        level=logging.DEBUG)
    main()
