import logging
import os
from itertools import product
from typing import Dict, List

from republic.helper.utils import get_project_dir
from republic.nlp.lm import train_lm
from republic.nlp.lm import make_character_dictionary
from republic.nlp.lm import make_train_test_split
from republic.nlp.ner import prep_training
from republic.nlp.ner import train
from republic.nlp.read import ParaReader, read_para_files_from_dir


ENTITY_TYPES = {
    'HOE', 'PER', 'COM', 'ORG', 'LOC', 'DAT', 'RES', 'NAM', 'single_layer',
    'FORWARD', 'DEC_START', 'RES_START', 'INCOMP', 'REF_PREV', 'VERB'
}

BEST_MODELS = [
        {
            'layer': 'COM', 'layer_model': 'COM', 'use_crf': True, 'use_rnn': True, 'reproject_embeddings': True,
            'use_context': True, 'use_finetuning': True, 'use_char': True, 'use_fasttext': False,
            'use_resolution': False, 'use_gysbert': True
        },
        {
            'layer': 'COM', 'layer_model': 'COM', 'use_crf': True, 'use_rnn': True, 'reproject_embeddings': True,
            'use_context': False, 'use_finetuning': True, 'use_char': True, 'use_fasttext': False,
            'use_resolution': False, 'use_gysbert': False},
        {
            'layer': 'DAT', 'layer_model': 'DAT', 'use_crf': True, 'use_rnn': True, 'reproject_embeddings': True,
            'use_context': True, 'use_finetuning': False, 'use_char': True, 'use_fasttext': False,
            'use_resolution': False, 'use_gysbert': False},
        {
            'layer': 'HOE', 'layer_model': 'HOE', 'use_crf': True, 'use_rnn': True, 'reproject_embeddings': True,
            'use_context': False, 'use_finetuning': True, 'use_char': True, 'use_fasttext': True,
            'use_resolution': False, 'use_gysbert': True},
        {
            'layer': 'LOC', 'layer_model': 'LOC', 'use_crf': True, 'use_rnn': True, 'reproject_embeddings': True,
            'use_context': False, 'use_finetuning': False, 'use_char': False, 'use_fasttext': True,
            'use_resolution': False, 'use_gysbert': True},
        {
            'layer': 'NAM', 'layer_model': 'single_layer', 'use_crf': True, 'use_rnn': True,
            'reproject_embeddings': True, 'use_context': True, 'use_finetuning': False, 'use_char': True,
            'use_fasttext': True, 'use_resolution': False, 'use_gysbert': True},
        {
            'layer': 'ORG', 'layer_model': 'ORG', 'use_crf': True, 'use_rnn': True, 'reproject_embeddings': True,
            'use_context': True, 'use_finetuning': True, 'use_char': True, 'use_fasttext': True,
            'use_resolution': False, 'use_gysbert': True},
        {
            'layer': 'PER', 'layer_model': 'PER', 'use_crf': True, 'use_rnn': True, 'reproject_embeddings': False,
            'use_context': False, 'use_finetuning': True, 'use_char': True, 'use_fasttext': False,
            'use_resolution': False, 'use_gysbert': True},
        {
            'layer': 'RES', 'layer_model': 'single_layer', 'use_crf': True, 'use_rnn': True,
            'reproject_embeddings': True, 'use_context': True, 'use_finetuning': False, 'use_char': False,
            'use_fasttext': True, 'use_resolution': False, 'use_gysbert': True}
]


def train_best_layers(best_model_params: List[Dict[str, any]], data_dir: Dict[str, str],
                      train_size=1.0, mini_batch_size=32, max_epochs=10):
    logging.basicConfig(filename='training_best_ner.log', level=logging.DEBUG)
    for params in best_model_params:
        layer = params['layer_model']
        print(f'training layer {layer}')
        print('params:', params)
        param_string = '-'.join([f"{param}_{params[param]}" for param in params if param.startswith('use_')])
        model_name = f"tdb_best_ner-layer_{params['layer']}-layer_model_{params['layer_model']}-{param_string}"
        print('model_name:', model_name)
        train_entity_tagger(layer_name=layer,
                            data_dir=data_dir[layer],
                            train_size=train_size, mini_batch_size=mini_batch_size, max_epochs=max_epochs,
                            use_crf=params['use_crf'],
                            use_rnn=params['use_rnn'],
                            use_context=params['use_context'],
                            use_char=params['use_char'],
                            use_fasttext=params['use_fasttext'],
                            use_gysbert=params['use_gysbert'],
                            use_resolution=params['use_resolution'],
                            use_finetuning=params['use_finetuning'],
                            reproject_embeddings=params['reproject_embeddings'],
                            model_name=model_name)


def train_layers(layers: List[str], data_dir: Dict[str, str], train_size=1.0, mini_batch_size=32, max_epochs=10):

    logging.basicConfig(filename='training_ner.log', level=logging.DEBUG)
    bool_options = [
        # 'use_crf',
        # 'use_rnn',
        'reproject_embeddings',
        'use_char',
        'use_context',
        'use_finetuning',
        # 'use_resolution',
        # 'use_gysbert',
        'use_gysbert2',
        'use_fasttext'
    ]
    for p in product([True, False], repeat=len(bool_options)):
        params = dict(zip(bool_options, p))
        params['use_crf'] = True
        params['use_rnn'] = True
        params['use_resolution'] = False
        params['use_gysbert'] = False
        if params['use_gysbert2'] is False:
            continue
        for layer in layers:
            print(f'training layer {layer}')
            print('params:', params)
            param_string = '-'.join([f"{param}_{params[param]}" for param in params])
            model_name = f'tdb_ner-layer_{layer}-{param_string}'
            print('model_name:', model_name)
            train_entity_tagger(layer_name=layer,
                                data_dir=data_dir[layer],
                                train_size=train_size, mini_batch_size=mini_batch_size, max_epochs=max_epochs,
                                use_crf=params['use_crf'],
                                use_rnn=params['use_rnn'],
                                use_context=params['use_context'],
                                use_char=params['use_char'],
                                use_fasttext=params['use_fasttext'],
                                use_gysbert=params['use_gysbert'],
                                use_gysbert2=params['use_gysbert2'],
                                use_resolution=params['use_resolution'],
                                use_finetuning=params['use_finetuning'],
                                reproject_embeddings=params['reproject_embeddings'],
                                model_name=model_name)


def train_entity_tagger(layer_name: str,
                        data_dir: str,
                        train_size: float = 1.0,
                        hidden_size=256,
                        model_max_length=512,
                        learning_rate: float = 0.05,
                        mini_batch_size: int = 32,
                        max_epochs: int = 10,
                        use_crf: bool = False,
                        use_rnn: bool = False,
                        reproject_embeddings: bool = False,
                        use_context: bool = False,
                        use_finetuning: bool = False,
                        use_resolution: bool = False,
                        use_char: bool = False,
                        use_fasttext: bool = False,
                        use_gysbert: bool = False,
                        use_gysbert2: bool = False,
                        model_name=None):
    trainer = prep_training(layer_name,
                            data_dir,
                            train_size=train_size,
                            hidden_size=hidden_size,
                            use_finetuning=use_finetuning,
                            use_context=use_context,
                            use_resolution=use_resolution,
                            use_char=use_char,
                            use_gysbert=use_gysbert,
                            use_gysbert2=use_gysbert2,
                            use_fasttext=use_fasttext,
                            use_crf=use_crf,
                            use_rnn=use_rnn,
                            reproject_embeddings=reproject_embeddings,
                            model_max_length=model_max_length)
    if trainer is not None:
        train(trainer, layer_name, train_size,
              learning_rate=learning_rate,
              mini_batch_size=mini_batch_size,
              max_epochs=max_epochs,
              model_name=model_name)


def train_language_model(para_dir: str, corpus_dir: str, is_forward_lm: bool = True,
                         character_level: bool = True, hidden_size=256,
                         sequence_length=512, nlayers: int = 1,
                         mini_batch_size: int = 32, max_epochs: int = 10):
    logging.basicConfig(filename='training_lm.log', level=logging.DEBUG)
    para_files = read_para_files_from_dir(para_dir)
    para_reader = ParaReader(para_files, ignorecase=False)
    make_train_test_split(corpus_dir, para_reader=para_reader)
    make_character_dictionary(corpus_dir)
    train_lm(corpus_dir, is_forward_lm=is_forward_lm, character_level=character_level,
             hidden_size=hidden_size, nlayers=nlayers, sequence_length=sequence_length,
             mini_batch_size=mini_batch_size, max_epochs=max_epochs)


def parse_args():
    argv = sys.argv[1:]
    # Define the getopt parameters
    try:
        opts, args = getopt.getopt(argv, 'g:e:l:s:r:m:t',
                                   ['gt_dir=', 'epochs=', 'layers=', 'train_size=',
                                    'learning_rate=', 'mini_batch_size=', 'type='])
        train_type = None
        gt_base_dir = None
        layers = ['single_layer']
        train_size = 1.0
        learing_rate = 0.05
        mini_batch_size = 16
        max_epochs = 10
        print(opts)
        for opt, arg in opts:
            if opt in {'-g', '--gt_dir'}:
                gt_base_dir = arg
            if opt in {'-e', '--epochs'}:
                max_epochs = int(arg)
            if opt in {'-l', '--layers'}:
                layers = arg
                print(f'arg layers: #{layers}#')
                if ':' in layers:
                    layers = layers.split(':')
                else:
                    layers = [layers]
                print(f'arg layers: #{layers}#')
                assert all([layer in ENTITY_TYPES for layer in layers])
            if opt in {'-s', '--train_size'}:
                train_size = float(arg)
            if opt in {'-r', '--learning_rate'}:
                learing_rate = float(arg)
            if opt in {'-m', '--mini_batch_size'}:
                mini_batch_size = int(arg)
            if opt in {'-t', '--type'}:
                print('option -t passed')
                train_type = arg
        if train_type == 'ner' and gt_base_dir is None:
            raise ValueError('training a NER tagger requires passing a ground truth dir (-g or --gt_dir) '
                             'inside ./ground_truth')
        return layers, gt_base_dir, train_size, learing_rate, mini_batch_size, max_epochs, train_type
    except getopt.GetoptError:
        # Print something useful
        print('usage: do_training.py --type <ner|lm>')
        raise


def do_train_lm():
    logging.basicConfig(filename='training_lm.log', level=logging.DEBUG)
    para_dir = 'data/paragraphs/loghi'
    corpus_dir = 'data/embeddings/flair_embeddings/corpus_loghi'

    para_files = read_para_files_from_dir(para_dir)
    para_reader = ParaReader(para_files, ignorecase=False)

    make_train_test_split(corpus_dir, para_reader=para_reader)
    make_character_dictionary(corpus_dir)

    train_lm(corpus_dir, is_forward_lm=True, character_level=True,
             hidden_size=256, nlayers=1, sequence_length=512,
             mini_batch_size=32, max_epochs=10)

    train_lm(corpus_dir, is_forward_lm=False, character_level=True,
             hidden_size=256, nlayers=1, sequence_length=512,
             mini_batch_size=32, max_epochs=10)


def get_data_dir(layers: List[str], gt_base_dir: str) -> Dict[str, str]:
    project_dir = get_project_dir()
    data_dir = {}
    for layer_name in layers:
        assert os.path.exists(project_dir), f"the project directory {project_dir} doesn't exist"
        data_dir[layer_name] = f'{project_dir}/ground_truth/{gt_base_dir}/flair_training/flair_training_{layer_name}'
        assert os.path.exists(data_dir[layer_name]), f"the data directory {data_dir[layer_name]} doesn't exist"
    return data_dir


def main():
    layers, gt_base_dir, train_size, learing_rate, mini_batch_size, max_epochs, train_type = parse_args()
    print('train_type:', train_type)
    if train_type == 'ner':
        data_dir = get_data_dir(layers, gt_base_dir)
        print('layers to train:', layers)
        train_layers(layers, data_dir, train_size=train_size, mini_batch_size=mini_batch_size, max_epochs=max_epochs)
        train_best_layers(BEST_MODELS, data_dir, train_size=train_size, mini_batch_size=mini_batch_size, max_epochs=max_epochs)
    elif train_type == 'lm':
        do_train_lm()
    else:
        raise ValueError(f"invalid train_type '{train_type}', must be 'ner' or 'lm'.")


if __name__ == "__main__":
    import getopt
    import sys
    main()
