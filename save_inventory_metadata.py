import json

from republic.elastic.republic_elasticsearch import initialize_es

rep_es = initialize_es(host_type='external')

inv_metadata = [rep_es.retrieve_inventory_metadata(inv_num) for inv_num in range(3760, 3865)]

with open('data/inventories/inventory_metadata.json', 'wt') as fh:
    json.dump(inv_metadata, fh)
