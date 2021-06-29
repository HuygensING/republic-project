from republic.data.delegate_database import abbreviated_delegates
from republic.data.stopwords import stopwords
from republic.fuzzy.fuzzy_keyword_searcher import FuzzyKeywordSearcher


def nm_to_delen(naam, stopwords=stopwords):
    nms = [n for n in naam.split(' ') if n not in stopwords]
    return nms


def delegates_to_keywords(abbreviated_delegates,
                          stopwords=stopwords,
                          exclude=['Heeren', 'van', 'met', 'Holland']):
    """TODO: better exclude"""
    stopwords.extend(exclude)
    keywords = list(abbreviated_delegates.name)
    kwrds = {key: nm_to_delen(key) for key in keywords}
    nwkw = {d: k for k in list(set(keywords)) for d in k.split(' ') if d not in stopwords}
    return nwkw


herenkeywords = delegates_to_keywords(abbreviated_delegates)


def make_herensearcher(keywords=herenkeywords):
    fuzzysearch_config = {'char_match_threshold': 0.7,
                          'ngram_threshold': 0.5,
                          'levenshtein_threshold': 0.5,
                          'ignorecase': False,
                          'ngram_size': 2,
                          'skip_size': 2}
    herensearcher = FuzzyKeywordSearcher(config=fuzzysearch_config)
    herensearcher.use_word_boundaries = False
    herensearcher.index_keywords(keywords=list(keywords.keys()))
    for k in keywords:
        for variant in keywords[k]:
            herensearcher.index_spelling_variant(k, variant=variant)
    return herensearcher


herensearcher = make_herensearcher(keywords=herenkeywords)