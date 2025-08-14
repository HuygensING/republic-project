import os

import republic.elastic.republic_elasticsearch as republic_elasticsearch
import run_attendancelist


def do_attendance_indexing(rep_es, year_start: int, year_end: int):
    message = f"Indexing attendance lists with spans for years {year_start}-{year_end}..."
    print(message)
    res_index = rep_es.config['resolutions_index']
    # print('do_inventory_attendance_list_indexing - index:', self.rep_es.config['resolutions_index'])
    for year in range(year_start, year_end + 1):
        errors = []
        try:
            att_spans_year = run_attendancelist.run(rep_es.es_anno, year, outdir=None,
                                                    verbose=True, tofile=False,
                                                    source_index=rep_es.config['resolutions_index'])
            if att_spans_year is None:
                return None
            for span_list in att_spans_year:
                # print(span_list['metadata']['zittingsdag_id'])
                # print(span_list['spans'])
                att_id = f'{span_list["metadata"]["zittingsdag_id"]}-attendance_list'
                att_list = rep_es.retrieve_attendance_list_by_id(att_id)
                att_list.attendance_spans = span_list["spans"]
                print(f"re-indexing attendance list {att_list.id} with {len(span_list['spans'])} spans")
                prov_url = rep_es.post_provenance(att_list.id, att_list.id, res_index, res_index)
                if 'provenance_url' not in att_list.metadata:
                    att_list.metadata['provenance_url'] = []
                elif isinstance(att_list.metadata['provenance_url'], str):
                    att_list.metadata['provenance_url'] = [att_list.metadata['provenance_url']]
                att_list.metadata['provenance_url'].append(prov_url)
                rep_es.index_attendance_list(att_list)
        except Exception as err:
            errors.append(err)
            print(f'Error - issue with attendance lists for year {year}')
            raise
        error_label = f"{len(errors)} errors" if len(errors) > 0 else "no errors"
        print(f"finished indexing attendance lists of years {year_start}-{year_end} with {error_label}")


def main():
    host_type = os.environ.get('REPUBLIC_HOST_TYPE')
    if not host_type:
        host_type = "external"
    rep_es = republic_elasticsearch.initialize_es(host_type=host_type, timeout=60)
    year_start = 1577
    year_end = 1796
    do_attendance_indexing(rep_es, year_start, year_end)


if __name__ == "__main__":
    main()
