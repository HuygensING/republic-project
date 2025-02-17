from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.phrase.phrase_model import PhraseModel

from ...model.republic_date_phrase_model import month_names_early, month_names_late
from ...data.delegate_database import get_raa_db, read_ekwz
from ...data.stopwords import stopwords as default_stopwords


fuzzysearch_config = {
    "char_match_threshold": 0.8,
    "ngram_threshold": 0.6,
    "levenshtein_threshold": 0.5,
    "ignorecase": False,
    "ngram_size": 3,
    "skip_size": 1,
}


def nm_to_delen(naam, stopwords=None):
    if stopwords is None:
        stopwords = default_stopwords
    nms = [n for n in naam.split(' ') if n not in stopwords]
    return nms


def delegates_to_keywords(abbreviated_delegates=None,
                          stopwords=None,
                          exclude=None):
    """TODO: better exclude"""
    if abbreviated_delegates is None:
        abbreviated_delegates = get_raa_db()
    if stopwords is None:
        stopwords = default_stopwords
    if exclude is None:
        exclude = ['Heeren', 'van', 'met', 'Holland']
    stopwords.extend(exclude)
    keywords = list(abbreviated_delegates.name)
    kwrds = {key: nm_to_delen(key) for key in keywords}
    nwkw = {d: k for k in list(set(keywords)) for d in k.split(' ') if d not in stopwords}
    return nwkw


herenkeywords = delegates_to_keywords(get_raa_db())


def make_herensearcher(keywords=None):
    if keywords is None:
        abbreviated_delegates = get_raa_db()
        keywords = delegates_to_keywords(abbreviated_delegates)
    fuzzysearch_config = {'char_match_threshold': 0.7,
                          'ngram_threshold': 0.5,
                          'levenshtein_threshold': 0.5,
                          'ignorecase': False,
                          'ngram_size': 2,
                          'skip_size': 2}
    herensearcher = FuzzyPhraseSearcher(config=fuzzysearch_config)
    variants = [{'phrase': k, 'label':k, 'variants': v} for k, v in keywords.items()]
    phrase_model = PhraseModel(model=variants)
    herensearcher.index_phrase_model(phrase_model=phrase_model)
    return herensearcher


herensearcher = make_herensearcher(keywords=herenkeywords)


def make_junksweeper(ekwz):
    provincies = ['Holland', 'Zeeland', 'West-Vriesland', 'Gelderland', 'Overijssel', 'Utrecht', 'Friesland']
    months = month_names_early + month_names_late
    indexkeywords = months + provincies
    junksweeper = FuzzyPhraseSearcher(config=fuzzysearch_config)
    variants = [{'phrase': k, 'label':'junk', 'variants': v} for k, v in ekwz.items()]
    phrase_model = PhraseModel(model=variants, config=fuzzysearch_config)
    phrase_model.add_phrases(indexkeywords)
    junksweeper.index_phrase_model(phrase_model=phrase_model)
    return junksweeper


junksweeper = make_junksweeper(read_ekwz())
