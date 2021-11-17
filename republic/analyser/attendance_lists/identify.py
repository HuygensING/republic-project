import re
import pandas as pd
from fuzzy_search.fuzzy_string import score_levenshtein_similarity_ratio


def identify(name: str,
             df: pd.DataFrame,
             year: int,
             window: int,
             sg=True,
             fuzzy=False,
             exact_year=True,
             delegate=False):
    window = window
    yearmin = int(year) - window
    yearmax = int(year) + window
    year = pd.Interval(yearmin, yearmax, closed="both")
    if fuzzy:
        mask = df["name"].apply(lambda x: score_levenshtein_similarity_ratio(x, name)) > 0.5
    else:
        mask = df["name"].str.contains(re.escape(name))
    if exact_year is True:
        mask = mask & df["p_interval"].apply(lambda x: x.overlaps(year))
    if sg is True:
        mask = mask & (df["sg"] == True)
    result = df.loc[mask]
    return result


# #### iterative search

# iterative identification (see above)
# delegate is not yet included as conclusion as function at staten generaal may be enough distinction

def iterative_search(name: str, year: int, df: pd.DataFrame, debug=False):
    scoreboard = {1: 1.0, 2: 0.9, 3: 0.8, 4: 0.7, 5: 0.6, 6: 0.5, 7: 0.4, 8: 0.3}
    score = 0
    for item in ({'window': 0, 'fuzzy': False, 'sg': True, 'delegate': True, 'exact_year': True},
                 {'window': 30, 'fuzzy': False, 'sg': True, 'delegate': True, 'exact_year': False},
                 {'window': 10, 'fuzzy': True, 'sg': True, 'delegate': True, 'exact_year': True},
                 {'window': 30, 'fuzzy': True, 'sg': True, 'delegate': True, 'exact_year': False},
                 {'window': 0, 'fuzzy': False, 'sg': False, 'delegate': True, 'exact_year': True},
                 {'window': 30, 'fuzzy': False, 'sg': False, 'delegate': True, 'exact_year': False},
                 {'window': 10, 'fuzzy': True, 'sg': False, 'delegate': True, 'exact_year': True},
                 {'window': 30, 'fuzzy': True, 'sg': False, 'delegate': True, 'exact_year': False},):

        score += 1
        result = identify(name=name, df=df, year=year, **item)
        if debug is True:
            print('window', item['window'],
                  'fuzzy', item['fuzzy'],
                  'sg', item['sg'],
                  'exact_year', item['exact_year'], score, len(result))
        if len(result) > 0:
            result = result.copy()
            result['score'] = scoreboard.get(score) or 0.0
            if debug is True:
                print('window', item['window'],
                      'fuzzy', item['fuzzy'],
                      'sg', item['sg'],
                      'exact_year', item['exact_year'], score, len(result))
            return result
        if score == 8 and len(result) == 0:
            result['score'] = 0.0
            return result
