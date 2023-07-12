import sys

from republic.tag.train import prep_training
from republic.tag.train import train


ENTITY_TYPES = {'HOE', 'PER', 'COM', 'ORG', 'LOC', 'DAT', 'REF'}


def train_entity_tagger(layer_name: str, train_size: float = 1.0, hidden_size=256,
             model_max_length=512, learning_rate: float = 0.05,
             mini_batch_size: int = 32, max_epochs: int = 10):
    trainer = prep_training(layer_name, train_size, hidden_size, model_max_length)
    train(trainer, layer_name, train_size, learning_rate=learning_rate,
          mini_batch_size=mini_batch_size, max_epochs=max_epochs)


def parse_args():
    argv = sys.argv[1:]
    # Define the getopt parameters
    try:
        opts, args = getopt.getopt(argv, 'l:s:r:m',
                                   ['layers=', 'train_size=', 'learning_rate=', 'mini_batch_size='])
        layers = ['single_layer']
        train_size = 1.0
        learing_rate = 0.05
        mini_batch_size = 32
        for opt, arg in opts:
            if opt in {'-l', '--layer'}:
                layer = arg
                if ':' in layer:
                    layers = layer.split(':')
                else:
                    layers = [layer]
                assert all([layer in ENTITY_TYPES for layer in layers])
            if opt in {'-s', '--train_size'}:
                train_size = int(arg)
            if opt in {'-r', '--learning_rate'}:
                learing_rate = int(arg)
            if opt in {'-m', '--mini_batch_size'}:
                mini_batch_size = arg
        return layers, train_size, learing_rate, mini_batch_size
    except getopt.GetoptError:
        # Print something useful
        print('usage: add.py -s <start_year> -e <end_year> -i <indexing_step> -n <num_processes')
        sys.exit(2)


def main():
    layers, train_size, learing_rate, mini_batch_size = parse_args()
    for layer in layers:
        print(f'training layer {layer}')
        train_entity_tagger(layer_name=layer, train_size=train_size, mini_batch_size=mini_batch_size)


if __name__ == "__main__":
    import getopt
    import sys
    main()

