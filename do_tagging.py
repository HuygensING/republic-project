import glob
import gzip
import os
import pickle

from flair.models import SequenceTagger

from republic.helper.utils import get_project_dir
from republic.tag.entities import tag_resolution


def read_paragraphs(para_file: str):
    with gzip.open(para_file, 'rt') as fh:
        for line in fh:
            yield line.strip().split('\t')
    return None


def read_para_files(para_dir: str):
    return glob.glob(os.path.join(para_dir, 'resolutions*.tsv.gz'))


def load_model(layer_name: str, taggers_dir: str, num_epochs: int):
    model_dir = os.path.join(taggers_dir, f'ner-tbd-{layer_name}-train_1.0-epochs_{num_epochs}')
    print(model_dir)
    return SequenceTagger.load(f'{model_dir}/final-model.pt')


def tag_paragraphs(para_file: str, layer_name: str, model: SequenceTagger, entities_dir: str):
    inv_num = para_file.split('-')[-1][:4]
    entities_file = os.path.join(entities_dir, f"entity_annotations-layer_{layer_name}-inv_{inv_num}.pcl")
    annotations = []
    for year, res_id, para_type, text in read_paragraphs(para_file):
        annos = tag_resolution(text, res_id, model)
        annotations.extend(annos)
        print(res_id, layer_name, len(annos), len(annotations))
    with open(entities_file, 'wb') as fh:
        pickle.dump(annotations, fh)


def main():
    project_dir = get_project_dir()
    flair_dir = os.path.join(project_dir, 'data/embeddings/flair_embeddings')
    entities_dir = 'data/entities'
    taggers_dir = os.path.join(flair_dir, "resources/taggers")
    para_dir = 'data/paragraphs/loghi'
    num_epochs = 15
    layers = ['DAT', 'HOE', 'LOC', 'ORG', 'COM', 'PER', 'RES', 'NAM']

    para_files = read_para_files(para_dir)
    for layer_name in layers:
        model = load_model(layer_name, taggers_dir, num_epochs)
        for para_file in para_files:
            tag_paragraphs(para_file, layer_name, model, entities_dir)


if __name__ == "__main__":
    main()
