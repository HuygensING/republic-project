from typing import Dict, List

import flair
from flair.embeddings import TransformerDocumentEmbeddings
from flair.data import Sentence
import torch
import torch.autograd as autograd
import torch.nn.functional as F
from torch import nn


SPATIAL_FIELDS = [
    'left', 'right', 'top', 'bottom',
    'left_base_x', 'left_base_y',
    'dist_to_prev', 'dist_to_next',
    'indent', 'indent_frac',
    # words
    'weekdays', 'months', 'tokens',
    # characters
    'line_break_chars', 'chars', 'digit', 'whitespace', 'quote',
    'punctuation', 'upper_alpha', 'lower_alpha', 'rare_char'
]


class LSTMLineTagger(nn.Module):

    def __init__(self, char_embedding_dim,
                 spatial_hidden_dim: int, char_hidden_dim: int,
                 num_spatial_features: int,
                 char_line_size: int, char_vocab_size: int, line_class_size: int,
                 bidirectional: bool = False):
        super(LSTMLineTagger, self).__init__()
        self.spatial_hidden_dim = spatial_hidden_dim
        self.num_spatial_features = num_spatial_features
        self.char_hidden_dim = char_hidden_dim
        self.char_embedding_dim = char_embedding_dim
        self.char_line_size = char_line_size
        self.char_vocab_size = char_vocab_size
        self.line_class_size = line_class_size
        self.bidirectional = bidirectional
        self.combined_hidden_dim = spatial_hidden_dim + char_hidden_dim

        if bidirectional is True:
            self.spatial_hidden_dim = self.spatial_hidden_dim * 2
            self.char_hidden_dim = self.char_hidden_dim * 2
            self.combined_hidden = self.combined_hidden_dim * 2

        # Initialise hidden state
        self.spatial_hidden = self.init_hidden(spatial_hidden_dim)
        self.char_hidden = self.init_hidden(char_hidden_dim)
        self.combined_hidden = self.init_hidden(self.combined_hidden_dim)

        # Char embedding and encoding into char-lvl representation of words (c_w):
        self.char_embeddings = nn.Embedding(char_vocab_size, char_embedding_dim)
        self.char_lstm = nn.LSTM(char_line_size * char_embedding_dim, char_hidden_dim,
                                 bidirectional=bidirectional)

        # The spatial model
        self.spatial_linear = nn.Linear(num_spatial_features, spatial_hidden_dim)
        self.spatial_lstm = nn.LSTM(num_spatial_features, spatial_hidden_dim,
                                    bidirectional=bidirectional)

        # The combined model
        self.combined_lstm = nn.LSTM(spatial_hidden_dim + char_hidden_dim, self.combined_hidden_dim,
                                     bidirectional=bidirectional)

        # The linear layer that maps from hidden state space to word space
        self.hidden2class = nn.Linear(self.combined_hidden_dim, line_class_size)

    @property
    def config(self):
        return {
            'model_class': self.__class__.__name__,
            'char_embedding_dim': self.char_embedding_dim,
            'spatial_hidden_dim': self.spatial_hidden_dim,
            'char_hidden_dim': self.char_hidden_dim,
            'num_spatial_features': self.num_spatial_features,
            'char_vocab_size': self.char_vocab_size,
            'char_line_size': self.char_line_size,
            'line_class_size': self.line_class_size,
            'bidirectional': self.bidirectional
        }

    @staticmethod
    def load_from_config(config: Dict[str, any]):
        model = LSTMLineTagger(config['char_embedding_dim'],
                               config['spatial_hidden_dim'],
                               config['char_hidden_dim'],
                               config['num_spatial_features'],
                               config['char_line_size'],
                               config['char_vocab_size'],
                               config['line_class_size'],
                               config['bidirectional'])
        model.load_state_dict(torch.load(config['model_file']), strict=False)
        model.eval()
        return model

    @staticmethod
    def init_hidden(size):
        return (autograd.Variable(torch.zeros(1, size)),
                autograd.Variable(torch.zeros(1, size)))

    def forward(self, spatial_features, char_features):
        # print(spatial_features.shape)
        # print(self.spatial_hidden)
        # print(spatial_features.view(len(spatial_features), 1, -1))
        # linear_output, self.spatial_hidden = self.spatial_linear(spatial_features, self.spatial_hidden)
        char_embeds = self.char_embeddings(char_features)
        # print(char_embeds)

        char_lstm_output, self.char_hidden = self.char_lstm(char_embeds.view(len(char_features), -1))
        spatial_lstm_output, self.spatial_hidden = self.spatial_lstm(spatial_features, self.spatial_hidden)

        combined_hidden = torch.cat([spatial_lstm_output, char_lstm_output], dim=1)
        combined_lstm_output, self.combined_hidden = self.combined_lstm(combined_hidden)
        # print(combined_lstm_output.shape)

        # Map word LSTM output to POS tag space
        class_space = self.hidden2class(combined_lstm_output)
        class_scores = F.log_softmax(class_space, dim=1)
        return class_scores


class LSTMLineNgramTagger(nn.Module):

    def __init__(self, ngram_embedding_dim,
                 spatial_hidden_dim, ngram_hidden_dim,
                 num_spatial_features, ngram_line_sizes, ngram_vocab_sizes, line_class_size,
                 bidirectional: bool = False):
        super(LSTMLineNgramTagger, self).__init__()
        self.ngram_embedding_dim = ngram_embedding_dim
        self.num_spatial_features = num_spatial_features
        self.ngram_line_sizes = ngram_line_sizes
        self.ngram_vocab_sizes = ngram_vocab_sizes
        self.spatial_hidden_dim = spatial_hidden_dim
        self.ngram_hidden_dim = ngram_hidden_dim
        self.line_class_size = line_class_size
        num_ngram_sizes = len(ngram_vocab_sizes)
        self.combined_hidden_dim = spatial_hidden_dim + self.ngram_hidden_dim * num_ngram_sizes

        # Initialise hidden state
        self.spatial_hidden = self.init_hidden(spatial_hidden_dim)
        self.ngram_hidden = {}
        for ngram_size in ngram_vocab_sizes:
            self.ngram_hidden[ngram_size] = self.init_hidden(self.ngram_hidden_dim)
        self.combined_hidden = self.init_hidden(self.combined_hidden_dim)

        # Ngram embedding and encoding into ngram-lvl representation of words (c_w):
        self.ngram_embeddings = {}
        self.ngram_lstm = {}
        for ngram_size in ngram_vocab_sizes:
            self.ngram_embeddings[ngram_size] = nn.Embedding(ngram_vocab_sizes[ngram_size],
                                                             ngram_embedding_dim)
            self.ngram_lstm[ngram_size] = nn.LSTM(ngram_line_sizes[ngram_size] * ngram_embedding_dim,
                                                  ngram_hidden_dim, bidirectional=bidirectional)

        # The spatial model
        self.spatial_linear = nn.Linear(num_spatial_features, spatial_hidden_dim)
        self.spatial_lstm = nn.LSTM(num_spatial_features, spatial_hidden_dim, bidirectional=bidirectional)

        # The combined model
        self.combined_lstm = nn.LSTM(spatial_hidden_dim + self.ngram_hidden_dim * num_ngram_sizes,
                                     self.combined_hidden_dim, bidirectional=bidirectional)

        # The linear layer that maps from hidden state space to word space
        self.hidden2class = nn.Linear(self.combined_hidden_dim, line_class_size)

    @property
    def config(self):
        return {
            'model_class': self.__class__.__name__,
            'ngram_embedding_dim': self.ngram_embedding_dim,
            'spatial_hidden_dim': self.spatial_hidden_dim,
            'ngram_hidden_dim': self.ngram_hidden_dim,
            'num_spatial_features': self.num_spatial_features,
            'ngram_vocab_sizes': self.ngram_vocab_sizes,
            'ngram_line_sizes': self.ngram_line_sizes,
            'line_class_size': self.line_class_size
        }

    @staticmethod
    def load_from_config(config: Dict[str, any]):
        model = LSTMLineNgramTagger(config['ngram_embedding_dim'],
                                    config['spatial_hidden_dim'],
                                    config['ngram_hidden_dim'],
                                    config['num_spatial_features'],
                                    config['ngram_line_sizes'],
                                    config['ngram_vocab_sizes'],
                                    config['line_class_size'],
                                    config['bidirectional'])
        model.load_state_dict(torch.load(config['model_file']), strict=False)
        model.eval()
        return model

    @staticmethod
    def init_hidden(size):
        return (autograd.Variable(torch.zeros(1, size)),
                autograd.Variable(torch.zeros(1, size)))

    def forward(self, spatial_features, ngram_features):
        # print(spatial_features.shape)
        # print(self.spatial_hidden)
        # print(spatial_features.view(len(spatial_features), 1, -1))
        # linear_output, self.spatial_hidden = self.spatial_linear(spatial_features, self.spatial_hidden)
        ngram_lstm_output = []
        for ngram_size in self.ngram_embeddings:
            ngram_embeds = self.ngram_embeddings[ngram_size](ngram_features[ngram_size])
            view = ngram_embeds.view(len(ngram_features[ngram_size]), -1)
            ngram_lstm_output_, self.ngram_hidden[ngram_size] = self.ngram_lstm[ngram_size](view)
            ngram_lstm_output.append(ngram_lstm_output_)
        spatial_lstm_output, self.spatial_hidden = self.spatial_lstm(spatial_features, self.spatial_hidden)

        combined_hidden = torch.cat([spatial_lstm_output] + ngram_lstm_output, dim=1)
        combined_lstm_output, self.combined_hidden = self.combined_lstm(combined_hidden)

        # Map word LSTM output to line class space
        class_space = self.hidden2class(combined_lstm_output)
        class_scores = F.log_softmax(class_space, dim=1)
        return class_scores


class LSTMLineTaggerGysBERT(nn.Module):

    def __init__(self, char_embedding_dim,
                 spatial_hidden_dim: int, char_hidden_dim: int, sentence_hidden_dim: int,
                 num_spatial_features: int,
                 char_line_size: int, char_vocab_size: int, line_class_size: int,
                 bidirectional: bool = False):
        super(LSTMLineTaggerGysBERT, self).__init__()
        self.spatial_hidden_dim = spatial_hidden_dim
        self.num_spatial_features = num_spatial_features
        self.char_hidden_dim = char_hidden_dim
        self.char_embedding_dim = char_embedding_dim
        self.char_line_size = char_line_size
        self.char_vocab_size = char_vocab_size
        self.line_class_size = line_class_size
        self.sentence_hidden_dim = sentence_hidden_dim
        self.bidirectional = bidirectional
        self.combined_hidden_dim = spatial_hidden_dim + char_hidden_dim + sentence_hidden_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device = torch.device("cpu")
        flair.device = self.device

        if bidirectional is True:
            self.spatial_hidden_dim = self.spatial_hidden_dim * 2
            self.char_hidden_dim = self.char_hidden_dim * 2
            self.sentence_hidden_dim = self.sentence_hidden_dim * 2
            self.combined_hidden = self.combined_hidden_dim * 2

        # Initialise hidden state
        self.spatial_hidden = self.init_hidden(spatial_hidden_dim)
        self.char_hidden = self.init_hidden(char_hidden_dim)
        self.sentence_hidden = self.init_hidden(sentence_hidden_dim)
        self.combined_hidden = self.init_hidden(self.combined_hidden_dim)

        # Char embedding and encoding into char-lvl representation of words (c_w):
        self.char_embeddings = nn.Embedding(char_vocab_size, char_embedding_dim)
        self.char_lstm = nn.LSTM(char_line_size * char_embedding_dim, char_hidden_dim,
                                 bidirectional=bidirectional)

        # The sentence embedding model based on GysBERT
        self.sentence_embeddings = TransformerDocumentEmbeddings('emanjavacas/GysBERT')
        self.sentence_lstm = nn.LSTM(self.sentence_embeddings.embedding_length, sentence_hidden_dim,
                                     bidirectional=bidirectional)

        # The spatial model
        self.spatial_linear = nn.Linear(num_spatial_features, spatial_hidden_dim)
        self.spatial_lstm = nn.LSTM(num_spatial_features, spatial_hidden_dim,
                                    bidirectional=bidirectional)

        # The combined model
        self.combined_lstm = nn.LSTM(spatial_hidden_dim + char_hidden_dim + sentence_hidden_dim,
                                     self.combined_hidden_dim, bidirectional=bidirectional)

        # The linear layer that maps from hidden state space to word space
        self.hidden2class = nn.Linear(self.combined_hidden_dim, line_class_size)

        self.char_embeddings.to(self.device)
        self.char_lstm.to(self.device)
        self.sentence_embeddings.to(self.device)
        self.sentence_lstm.to(self.device)
        self.spatial_linear.to(self.device)
        self.spatial_lstm.to(self.device)
        self.combined_lstm.to(self.device)
        self.hidden2class.to(self.device)

    @property
    def config(self):
        return {
            'model_class': self.__class__.__name__,
            'char_embedding_dim': self.char_embedding_dim,
            'spatial_hidden_dim': self.spatial_hidden_dim,
            'char_hidden_dim': self.char_hidden_dim,
            'sentence_hidden_dim': self.sentence_hidden_dim,
            'num_spatial_features': self.num_spatial_features,
            'char_vocab_size': self.char_vocab_size,
            'char_line_size': self.char_line_size,
            'line_class_size': self.line_class_size,
            'bidirectional': self.bidirectional
        }

    @staticmethod
    def load_from_config(config: Dict[str, any]):
        model = LSTMLineTaggerGysBERT(config['char_embedding_dim'],
                                      config['spatial_hidden_dim'],
                                      config['char_hidden_dim'],
                                      config['sentence_hidden_dim'],
                                      config['num_spatial_features'],
                                      config['char_line_size'],
                                      config['char_vocab_size'],
                                      config['line_class_size'],
                                      config['bidirectional'])
        # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # model.load_state_dict(torch.load(config['model_file'], map_location=device), strict=False)
        model.load_state_dict(torch.load(config['model_file']), strict=False)
        model.eval()
        return model

    # @staticmethod
    def init_hidden(self, size):
        return (autograd.Variable(torch.zeros(1, size).to(self.device)),
                autograd.Variable(torch.zeros(1, size).to(self.device)))

    def forward(self, spatial_features, char_features, line_texts: List[str]):
        # print(spatial_features.shape)
        # print(self.spatial_hidden)
        # print(spatial_features.view(len(spatial_features), 1, -1))
        # linear_output, self.spatial_hidden = self.spatial_linear(spatial_features, self.spatial_hidden)
        try:
            char_embeds = self.char_embeddings(char_features.to(self.device))
        except RunTimeError:
            print(char_features)
            raise
        # print(char_embeds)

        # for line_text in line_texts:
        #     print(line_text)
        #     sentence = Sentence(line_text)
        if isinstance(line_texts, list) and isinstance(line_texts[0], str):
            sentences = self.sentence_embeddings.embed([Sentence(line_text) for line_text in line_texts])
            sentence_embeds = torch.stack([sentence.embedding for sentence in sentences])
            # sentence_embeds = sentence_embeds.to(self.device)
        else:
            sentence_embeds = line_texts

        char_lstm_output, self.char_hidden = self.char_lstm(char_embeds.view(len(char_features), -1))

        sentence_embeds = sentence_embeds.to(self.device)

        sentence_lstm_output, self.sentence_hidden = self.sentence_lstm(sentence_embeds)

        spatial_features = spatial_features.to(self.device)
        spatial_lstm_output, self.spatial_hidden = self.spatial_lstm(spatial_features, self.spatial_hidden)

        combined_hidden = torch.cat([spatial_lstm_output, char_lstm_output, sentence_lstm_output], dim=1)
        combined_lstm_output, self.combined_hidden = self.combined_lstm(combined_hidden)
        # print(combined_lstm_output.shape)

        # Map word LSTM output to POS tag space
        class_space = self.hidden2class(combined_lstm_output)
        class_scores = F.log_softmax(class_space, dim=1)
        return class_scores
