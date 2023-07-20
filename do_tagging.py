import glob
import gzip
import os
import pickle
import multiprocessing
from collections import defaultdict

from flair.models import SequenceTagger

from republic.helper.utils import get_project_dir
from republic.tag.entities import tag_resolution


ENTITY_TYPES = {'HOE', 'PER', 'COM', 'ORG', 'LOC', 'DAT', 'RES'}


def read_paragraphs(para_file: str):
    with gzip.open(para_file, 'rt') as fh:
        for line in fh:
            parts = line.strip().split('\t')
            if len(parts) != 4:
                continue
            yield parts
    return None


def read_para_files(para_dir: str):
    return sorted(glob.glob(os.path.join(para_dir, 'resolution*.tsv.gz')))


def load_model(model_dir: str):
    return SequenceTagger.load(f'{model_dir}/final-model.pt')


def tag_paragraphs(task):
    inv_num = task['para_file'].split('-')[-1][:4]
    entities_file = os.path.join(task['entities_dir'], f"entity_annotations-layer_{task['layer_name']}-inv_{inv_num}.pcl")
    annotations = []
    count = 0
    for year, para_id, para_type, text in read_paragraphs(task['para_file']):
        if para_type in {'marginalia'}:
            continue
        if count % 100 == 0:
            print(f"{task['layer_name']}\tinv: {inv_num}\tresolutions: {count: >8}\tannotations: {len(annotations): >8}")
        annos = tag_resolution(text, para_id, task['model'])
        annotations.extend(annos)
        prev_id = para_id
        count += 1
    print(f"{task['layer_name']}\tinv: {inv_num}\tresolutions: {count: >8}\tannotations: {len(annotations): >8}")
    with open(entities_file, 'wb') as fh:
        pickle.dump(annotations, fh)



def parse_args():
    argv = sys.argv[1:]
    # Define the getopt parameters
    try:
        opts, args = getopt.getopt(argv, 'l',
                                   ['layers='])
        layers = ['single_layer']
        for opt, arg in opts:
            if opt in {'-l', '--layers'}:
                layers = arg
                if ':' in layers:
                    layers = layers.split(':')
                else:
                    layers = [layers]
                assert all([layer in ENTITY_TYPES for layer in layers])
        print('training layers:', layers)
        return layers
    except getopt.GetoptError:
        # Print something useful
        print('usage: add.py -s <start_year> -e <end_year> -i <indexing_step> -n <num_processes')
        sys.exit(2)



def main():
    project_dir = get_project_dir()
    flair_dir = os.path.join(project_dir, 'data/embeddings/flair_embeddings')
    entities_dir = 'data/entities'
    taggers_dir = os.path.join(flair_dir, "resources/taggers")
    para_dir = 'data/paragraphs/loghi'
    para_files = read_para_files(para_dir)
    print('num para files:', len(para_files))

    num_epochs = 15
    num_processes = 4
    layers = ['DAT', 'HOE', 'LOC', 'ORG', 'COM', 'PER', 'RES']
    layers = parse_args()

    for layer_name in layers:
        model_dir = os.path.join(taggers_dir, f'ner-tbd-{layer_name}-train_1.0-epochs_{num_epochs}')
        model = load_model(model_dir)
        for para_file in para_files:
            task = {
                'para_file': para_file,
                'layer_name': layer_name,
                'model': model,
                'entities_dir': entities_dir
            }
            tag_paragraphs(task)


if __name__ == "__main__":
    import getopt
    import sys
    main()
