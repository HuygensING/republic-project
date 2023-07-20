import logging
import random
from typing import Iterable

from flair.data import Dictionary
from flair.models import LanguageModel
from flair.trainers.language_model_trainer import LanguageModelTrainer, TextCorpus


def get_train_test_validate_filenames(corpus_dir: str):
    train_dir = f"{corpus_dir}/train"
    test_file = f"{corpus_dir}/test.txt"
    validate_file = f"{corpus_dir}/valid.txt"
    return train_dir, test_file, validate_file


def make_train_test_split(corpus_dir: str, para_reader: Iterable):
    train_dir, test_file, validate_file = get_train_test_validate_filenames(corpus_dir)
    train_split = 0
    fh_test = open(test_file, 'wt', encoding="utf-8")
    fh_valid = open(validate_file, 'wt', encoding="utf-8")
    train_count = 0
    test_count, validate_count = 0, 0
    train_file = f'{corpus_dir}/temp'
    fh_train = open(train_file, 'wt', encoding="utf-8")
    paras_per_split = 1000000

    for year, para_id, para_type, text in para_reader:
        draw = random.random()
        # print(draw, train_count, train_file)
        if draw < 0.05:
            fh_test.write(text + '\n')
            test_count += 1
        elif draw < 0.1:
            fh_valid.write(text + '\n')
            validate_count += 1
        else:
            if train_count % paras_per_split == 0:
                train_split += 1
                train_file = f'{train_dir}/train_split_{train_split}'
                fh_train.close()
                fh_train = open(train_file, 'wt', encoding="utf-8")
            fh_train.write(text + '\n')
            train_count += 1
    print(f'paragraphs - train: {train_count}\tvalidate: {validate_count}\ttest: {test_count}')

    fh_test.close()
    fh_valid.close()
    fh_train.close()


def make_character_dictionary(corpus_dir: str):
    train_dir, test_file, validate_file = get_train_test_validate_filenames(corpus_dir)

    char_dictionary: Dictionary = Dictionary()

    # counter object
    import collections
    char_freq = collections.Counter()

    processed = 0

    import glob
    files = glob.glob(f'{corpus_dir}/**/*')
    files += [test_file, validate_file]

    logging.info('making character dictionary')
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            tokens = 0
            for line in f:
                processed += 1
                chars = list(line)
                tokens += len(chars)

                # Add chars to the dictionary
                char_freq.update(chars)

                # comment this line in to speed things up (if the corpus is too large)
                # if tokens > 50000000: break

        # break

    total_count = sum(char_freq.values())

    logging.info(f'\ttotal character count: {total_count}')
    logging.info(f'\ttotal paragraph count: {processed}')

    cumu = 0
    idx = 0
    for letter, count in char_freq.most_common():
        cumu += count
        percentile = (cumu / total_count)

        # comment this line in to use only top X percentile of chars, otherwise filter later
        # if percentile < 0.00001: break

        char_dictionary.add_item(letter)
        idx += 1
        logging.info('%d\t%s\t%7d\t%7d\t%f' % (idx, letter, count, cumu, percentile))

    import pickle
    with open(f'{corpus_dir}/republic_char_mappings', 'wb') as f:
        mappings = {
            'idx2item': char_dictionary.idx2item,
            'item2idx': char_dictionary.item2idx
        }
        pickle.dump(mappings, f)


def train_lm(corpus_dir: str, is_forward_lm: bool = True, character_level: bool = True,
             hidden_size: int = 128, nlayers: int = 1, sequence_length: int = 250,
             mini_batch_size: int = 100, max_epochs: int = 10):
    # are you training a forward or backward LM?

    # load the default character dictionary
    dictionary = Dictionary.load_from_file(f'{corpus_dir}/republic_char_mappings')

    # get your corpus, process forward and at the character level
    corpus = TextCorpus(corpus_dir,
                        dictionary,
                        is_forward_lm,
                        character_level=character_level)

    # instantiate your language model, set hidden size and number of layers
    language_model = LanguageModel(dictionary,
                                   is_forward_lm,
                                   hidden_size=hidden_size,
                                   nlayers=nlayers)

    # train your language model
    trainer = LanguageModelTrainer(language_model, corpus)

    trainer.train(f'{corpus_dir}/resources/taggers/language_model_bw',
                  sequence_length=sequence_length,
                  mini_batch_size=mini_batch_size,
                  max_epochs=max_epochs)
    return None
