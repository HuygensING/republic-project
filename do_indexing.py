import glob
import gzip
import os
import pickle

from flair.models import SequenceTagger

from republic.helper.utils import get_project_dir
from republic.nlp.entities import tag_resolution


def read_paragraphs(para_file: str):
    with gzip.open(para_file, 'rt') as fh:
        for line in fh:
            parts = line.strip().split('\t')
            if len(parts) != 4:
                continue
            yield parts
    return None


def read_para_files(para_dir: str):
    return glob.glob(os.path.join(para_dir, 'resolution*.tsv.gz'))


def load_model(model_dir: str):
    return SequenceTagger.load(f'{model_dir}/final-model.pt')


def tag_paragraphs(task):
    inv_num = task['para_file'].split('-')[-1][:4]
    entities_file = os.path.join(task['entities_dir'], f"entity_annotations-layer_{task['layer_name']}-inv_{inv_num}.pcl")
    annotations = []
    for year, res_id, para_type, text in read_paragraphs(task['para_file']):
        if para_type in {'marginalia'}:
            continue
        annos = tag_resolution(text, res_id, task['model'])
        annotations.extend(annos)
        print(res_id)
    with open(entities_file, 'wb') as fh:
        pickle.dump(annotations, fh)


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
    main()
