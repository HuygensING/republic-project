import tarfile
import datetime
import logging
import xml

from elasticsearch.exceptions import ElasticsearchException

from republic.elastic.republic_elasticsearch import initialize_es
import republic.parser.pagexml.republic_pagexml_parser as pagexml_parser

rep_es = initialize_es(host_type="internal", timeout=60)


def index_scan(inv_file, file_content, inv_metadata):
        try:
            scan = pagexml_parser.get_scan_pagexml(inv_file, pagexml_data=file_content, inv_metadata=inv_metadata)
            # print(scan.id, scan.stats)
            rep_es.index_scan(scan)
        except (xml.parsers.expat.ExpatError, ValueError, IndexError, KeyError, TypeError, ElasticsearchException, AttributeError) as err:
            print(f'Error parsing file {inv_file} - {err}')
            logging.error(f'Error parsing file {inv_file} - {err}')
            pass


def main():
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
