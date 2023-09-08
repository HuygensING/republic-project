import os.path

from flair.data import Corpus
from flair.datasets import ColumnCorpus
from flair.embeddings import WordEmbeddings, StackedEmbeddings, CharLMEmbeddings, FlairEmbeddings
from flair.embeddings import FastTextEmbeddings
from flair.embeddings import TransformerWordEmbeddings
from flair.models import SequenceTagger
from flair.trainers import ModelTrainer
from transformers import RobertaForMaskedLM

from republic.helper.utils import get_project_dir


def prep_corpus(project_dir: str, layer_name: str, train_size: float):
    data_dir = f'{project_dir}/ground_truth/entities/flair_training-17th_18th/flair_training_17th_18th_{layer_name}'
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


def prep_embeddings(flair_dir: str,
                    use_context: bool = False,
                    use_finetuning: bool = False,
                    use_resolution: bool = False,
                    use_gysbert: bool = False,
                    use_fasttext: bool = False,
                    model_max_length: int = 512):
    # resolution_bert = RobertaForMaskedLM.from_pretrained('data/models/resolution_bert')
    # fasttext_embeddings = FastTextEmbeddings('data/embeddings/gensim/win_10')
    # fasttext_embeddings = FastTextEmbeddings('data/embeddings/gensim/win_10/fasttext-dim_384-window_10-min_count_100-case_lower')
    resolution_embeddings = TransformerWordEmbeddings('data/models/resolution_bert',
                                                layers='-1',
                                                subtoken_pooling="first",
                                                fine_tune=use_finetuning,
                                                use_context=use_context,
                                                allow_long_sentences=False,
                                                model_max_length=model_max_length)
    gysbert_embeddings = TransformerWordEmbeddings('emanjavacas/GysBERT',
                                                   layers="-1",
                                                   subtoken_pooling="first",
                                                   fine_tune=use_finetuning,
                                                   use_context=use_context,
                                                   allow_long_sentences=False,
                                                   model_max_length=model_max_length)
    embedding_types = [
        FlairEmbeddings(f'{flair_dir}/resources/taggers/language_model_bw_char/best-lm.pt'),
        FlairEmbeddings(f'{flair_dir}/resources/taggers/language_model_fw_char/best-lm.pt'),
        # WordEmbeddings(''),
        # CharacterEmbeddings(),
        # resolution_bert,
        # fasttext_embeddings,
        # gysbert_embeddings
    ]
    if use_fasttext:
        embedding_types.append(fasttext_embeddings)
    if use_resolution:
        embedding_types.append(resolution_embeddings)
    if use_gysbert:
        embedding_types.append(gysbert_embeddings)

    return StackedEmbeddings(embeddings=embedding_types)


def prep_trainer(corpus: Corpus, hidden_size, embeddings: StackedEmbeddings,
                 use_crf: bool = False,
                 use_rnn: bool = False,
                 reproject_embeddings: bool = False):
    label_type = 'ner'

    label_dict = corpus.make_label_dictionary(label_type=label_type)
    tagger = SequenceTagger(hidden_size=hidden_size,
                            embeddings=embeddings,
                            tag_dictionary=label_dict,
                            tag_type=label_type,
                            use_crf=use_crf,
                            use_rnn=use_rnn,
                            reproject_embeddings=reproject_embeddings)

    return ModelTrainer(tagger, corpus)


def get_flair_dir():
    project_dir = get_project_dir()
    return f'{project_dir}/data/embeddings/flair_embeddings/'


def prep_training(layer_name: str,
                  train_size: float = 1.0,
                  use_crf: bool = False,
                  use_rnn: bool = False,
                  reproject_embeddings: bool = False,
                  use_context: bool = False,
                  use_finetuning: bool = False,
                  use_resolution: bool = False,
                  use_gysbert: bool = False,
                  use_fasttext: bool = False,
                  hidden_size=256, model_max_length=512):
    project_dir = get_project_dir()
    assert os.path.exists(project_dir), f"the project directory {project_dir} doesn't exist"
    flair_dir = get_flair_dir()
    assert os.path.exists(flair_dir), f"the flair directory {flair_dir} doesn't exist"

    corpus: Corpus = prep_corpus(project_dir, layer_name, train_size)

    embeddings = prep_embeddings(flair_dir,
                                 use_finetuning=use_finetuning,
                                 use_context=use_context,
                                 use_resolution=use_resolution,
                                 use_gysbert=use_gysbert,
                                 use_fasttext=use_fasttext,
                                 model_max_length=model_max_length)

    return prep_trainer(corpus, hidden_size, embeddings,
                        use_crf=use_crf,
                        use_rnn=use_rnn,
                        reproject_embeddings=reproject_embeddings)


def train(trainer, layer_name: str, train_size: float = 1.0, learning_rate: float = 0.05,
          mini_batch_size: int = 32, max_epochs: int = 10):
    flair_dir = get_flair_dir()
    model_dir = f'{flair_dir}/resources/taggers/ner-tbd-{layer_name}-' \
        f'train_{train_size}-epochs_{max_epochs}'
    results = trainer.train(model_dir,
                            learning_rate=learning_rate,
                            mini_batch_size=mini_batch_size,
                            max_epochs=max_epochs)

