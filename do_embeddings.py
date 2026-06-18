import itertools
from pathlib import Path
from typing import Iterable, List


from republic.helper.text_helper import ResolutionSentences
from republic.nlp.embeddings import make_embbedings, MODEL_TYPES


def do_train(sentences: Iterable[List[str]], model_dir: str | Path, model_date: str):
    min_counts = [5, 10, 100]
    window = [5, 20]
    vector_size = [100, 300]
    architectures = ['cbow', 'skip']
    epochs = 10
    workers = 4
    combinations = itertools.product(min_counts, window, vector_size, MODEL_TYPES, architectures)
    for min_count, window, vector_size, model_type, architecture in combinations:
        make_embbedings(sentences, model_dir, model_date, model_type, min_count=min_count, epochs=epochs,
                        vector_size=vector_size, window=window, workers=workers, architecture=architecture)


def main():
    model_date = "2026-03-25"
    model_dir = Path(f'resources/embeddings/embeddings-{model_date}')
    para_dir = Path('data/paragraphs/entities-Mar-2026/')
    para_files = list(para_dir.glob('*.tsv.gz'))
    len(para_files)
    sentences = ResolutionSentences(para_files[:1], as_doc=False, lowercase=True)
    do_train(sentences, model_dir, model_date)


if __name__ == "__main__":
    main()