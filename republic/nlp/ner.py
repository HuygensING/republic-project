import datetime
import os.path

from flair.data import Corpus
from flair.datasets import ColumnCorpus
from flair.embeddings import WordEmbeddings, StackedEmbeddings, CharLMEmbeddings, FlairEmbeddings
from flair.embeddings import TransformerWordEmbeddings
from flair.models import SequenceTagger
from flair.trainers import ModelTrainer

from republic.helper.utils import get_project_dir


def prep_corpus(project_dir: str, layer_name: str, train_size: float):
    data_dir = f'{project_dir}/ground_truth/entities/tag_de_besluiten/flair_training_{layer_name}'
    assert os.path.exists(data_dir), f"the data directory {data_dir} doesn't exist"
    train_file = os.path.join(data_dir, f'train_{train_size}.txt')
    test_file = os.path.join(data_dir, 'test.txt')
    validate_file = os.path.join(data_dir, 'validate.txt')
    assert os.path.exists(train_file), f"the train file {train_file} doesn't exist"
    assert os.path.exists(test_file), f"the test file {test_file} doesn't exist"
    assert os.path.exists(validate_file), f"the validate file {validate_file} doesn't exist"

    columns = {0: 'text', 1: 'ner'}

    return ColumnCorpus(data_dir, columns,
                        train_file=f'train_{train_size}.txt',
                        test_file='test.txt',
                        dev_file='validate.txt')


def prep_embeddings(flair_dir: str, model_max_length: int):
    gysbert_embeddings = TransformerWordEmbeddings('emanjavacas/GysBERT',
                                                   layers="-1",
                                                   allow_long_sentences=False,
                                                   model_max_length=model_max_length)
    embedding_types = [
        FlairEmbeddings(f'{flair_dir}/resources/taggers/language_model_bw_char/best-lm.pt'),
        FlairEmbeddings(f'{flair_dir}/resources/taggers/language_model_fw_char/best-lm.pt'),
        # WordEmbeddings(''),
        # CharacterEmbeddings(),
        gysbert_embeddings
    ]

    return StackedEmbeddings(embeddings=embedding_types)


def prep_trainer(corpus: Corpus, hidden_size, embeddings: StackedEmbeddings):
    label_type = 'ner'

    label_dict = corpus.make_label_dictionary(label_type=label_type)
    tagger = SequenceTagger(hidden_size=hidden_size,
                            embeddings=embeddings,
                            tag_dictionary=label_dict,
                            tag_type=label_type,
                            use_crf=True)

    return ModelTrainer(tagger, corpus)


def get_flair_dir():
    project_dir = get_project_dir()
    return f'{project_dir}/data/embeddings/flair_embeddings/'


def prep_training(layer_name: str, train_size: float = 1.0,
                  hidden_size=256, model_max_length=512):
    project_dir = get_project_dir()
    assert os.path.exists(project_dir), f"the project directory {project_dir} doesn't exist"
    flair_dir = get_flair_dir()
    assert os.path.exists(flair_dir), f"the flair directory {flair_dir} doesn't exist"

    corpus: Corpus = prep_corpus(project_dir, layer_name, train_size)

    embeddings = prep_embeddings(flair_dir, model_max_length)

    return prep_trainer(corpus, hidden_size, embeddings)


def train(trainer, layer_name: str, train_size: float = 1.0, learning_rate: float = 0.05,
          mini_batch_size: int = 32, max_epochs: int = 10):
    flair_dir = get_flair_dir()
    model_dir = f'{flair_dir}/resources/taggers/ner-tbd-{layer_name}-' \
                f'train_{train_size}-epochs_{max_epochs}'
    trainer.train(model_dir,
                  learning_rate=learning_rate,
                  mini_batch_size=mini_batch_size,
                  max_epochs=max_epochs)

