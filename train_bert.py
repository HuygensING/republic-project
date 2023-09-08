import os

from transformers import RobertaTokenizerFast

from republic.nlp.read import make_plain_text_file, read_para_files
from republic.nlp.lm import train_tokenizer
from republic.nlp.lm import make_bert_trainer


def train_bert(para_text_file: str, model_dir: str):
    print('training bert model')
    trainer = make_bert_trainer(model_dir, para_text_file, num_train_epochs=10,
                                per_device_mini_batch_size=64)
    trainer.train()
    trainer.save_model(model_dir)


def prep_tokenizer(para_text_file: str, model_dir: str):
    try:
        RobertaTokenizerFast.from_pretrained(model_dir)
        print('tokenizer already exists')
    except Exception:
        print('training tokenizer')
        train_tokenizer(para_text_file, model_dir)


def make_plain_text(para_text_file: str, para_dir: str):
    if os.path.exists(para_text_file) is False:
        print('making single plain text file')
        para_files = read_para_files(para_dir)
        make_plain_text_file(para_files, para_text_file)
    else:
        print('plain text file already exists')


if __name__ == "__main__":
    para_text_file = "data/resolutions/resolutions-paragraphs-loghi.txt"
    para_dir = 'data/paragraphs/loghi/'
    model_dir = 'data/models/resolution_bert'
    make_plain_text(para_text_file, para_dir)
    prep_tokenizer(para_text_file, model_dir)
    train_bert(para_text_file, model_dir)
