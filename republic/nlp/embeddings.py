import pickle
from collections import Counter
from pathlib import Path
from typing import Iterable, List

from gensim.models import Word2Vec
from gensim.models.fasttext import FastText

import republic.helper.text_helper as text_helper


MODEL_TYPES = ["word2vec", "fasttext"]


def make_embbedings(sentences: Iterable[List[str]], model_dir: str | Path, model_date: str,
                    model_type: str,
                    min_count: int, window: int, vector_size: int, workers: int, epochs: int,
                    architecture: str, min_n: int = 3, max_n : int = 6) -> None:
    filename = (f"{model_type}-resolutions-{model_date}-lowercase-win_{window}-"
                f"min_count_{min_count}-arch_{architecture}-vectors_{vector_size}.model")
    print(f"republic.nlp.embeddings.make_embeddings - training embeddings {filename}")
    sg = 1 if architecture == 'skip' else 0
    if model_type == "word2vec":
        model = Word2Vec(sentences=sentences, vector_size=vector_size, window=window, 
                        min_count=min_count, workers=workers, epochs=epochs, sg=sg)
    elif model_type == "fasttext":
        model = FastText(sentences=sentences, vector_size=vector_size, window=window, 
                        min_count=min_count, workers=workers, epochs=epochs, sg=sg,
                        min_n=min_n, max_n=max_n)
    else:
        raise ValueError(f"unexpected model type '{model_type}', must be one of ['word2vec', 'fasttext'].")
    print(f"\tsaving model")
    model_file = model_dir / filename
    model.save(str(model_file))
