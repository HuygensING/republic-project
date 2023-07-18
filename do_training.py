import sys

from republic.tag.train import prep_training
from republic.tag.train import train


ENTITY_TYPES = {'HOE', 'PER', 'COM', 'ORG', 'LOC', 'DAT', 'RES'}


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
        opts, args = getopt.getopt(argv, 'e:l:s:r:m',
                                   ['epochs=', 'layers=', 'train_size=', 'learning_rate=', 'mini_batch_size='])
        layers = ['single_layer']
        train_size = 1.0
        learing_rate = 0.05
        mini_batch_size = 32
        max_epochs = 10
        for opt, arg in opts:
            if opt in {'-e', '--epochs'}:
                max_epochs = int(arg)
            if opt in {'-l', '--layers'}:
                layers = arg
                if ':' in layers:
                    layers = layers.split(':')
                else:
                    layers = [layer]
                assert all([layer in ENTITY_TYPES for layer in layers])
            if opt in {'-s', '--train_size'}:
                train_size = int(arg)
            if opt in {'-r', '--learning_rate'}:
                learing_rate = float(arg)
            if opt in {'-m', '--mini_batch_size'}:
                print(arg)
                mini_batch_size = int(arg)
        print('training layers:', layers)
        return layers, train_size, learing_rate, mini_batch_size, max_epochs
    except getopt.GetoptError:
        # Print something useful
        print('usage: add.py -s <start_year> -e <end_year> -i <indexing_step> -n <num_processes')
        sys.exit(2)


def main():
    layers, train_size, learing_rate, mini_batch_size, max_epochs = parse_args()
    for layer in layers:
        print(f'training layer {layer}')
        train_entity_tagger(layer_name=layer, train_size=train_size, mini_batch_size=mini_batch_size, max_epochs=max_epochs)


if __name__ == "__main__":
    import getopt
    import sys
    main()

