import pandas as pd
import json
import ast
from .datamangler import make_abbreviated_delegates
from .abbr_delegates_to_pandas import abbreviated_delegates_from_excel
from .stopwords import stopwords
import pkg_resources


# DATA_PATH = pkg_resources.resource_filename('__name__', 'data/csvs')
PICKLE_FILE = pkg_resources.resource_filename(__name__, 'csvs/abbreviated_delegates.parquet')
PICKLE_FILE_FOUND = pkg_resources.resource_filename(__name__, 'csvs/found_deputies.parquet')
EXCEL_FILE_FOUND = pkg_resources.resource_filename(__name__, 'csvs/found_deputies.excel')
JUNK_JSON = pkg_resources.resource_filename(__name__, 'json/republic_junk.json')


def get_raa_db():
    try:
        abbr_delegates = pd.read_parquet(PICKLE_FILE) # change this to parquet? YES
        abbr_delegates['p_interval'] = abbr_delegates.apply(
            lambda x: pd.Interval(left=x["p_interval.left"], right=x["p_interval.right"]), axis=1)
        abbr_delegates['h_life'] = abbr_delegates.apply(
            lambda x: pd.Interval(left=x["h_life.left"], right=x["h_life.right"]), axis=1)
    except OSError:
        try:
            print("from excel")
            abbr_delegates = abbreviated_delegates_from_excel()
        except IOError:
            print("making abbreviated delegates")
            abbr_delegates = make_abbreviated_delegates()

        for interval in ['h_life', 'p_interval']:
            "fixing periods"
            ni = abbr_delegates[interval].apply(lambda x: ast.literal_eval(x))
            nii = ni.apply(lambda x: pd.Interval(int(x[0]), int(x[1])))
            abbr_delegates[interval] = nii
    return abbr_delegates

#
# if not pd.isna(geboortejaar) and geboortejaar.year < day and sterfjaar.year > day:
#     age_at_repr = len(pd.period_range(geboortejaar, day, freq="Y"))  # cool, though this gives impossible ages :-)
# else:
#     age_at_repr = pd.nan


abbreviated_delegates = get_raa_db()


def make_previously_matched(abbreviated_delegates=abbreviated_delegates, stopwords=stopwords):
    try:
        previously_matched = pd.read_parquet(PICKLE_FILE_FOUND)
    except (OSError, ValueError):
        previously_matched = pd.read_parquet(PICKLE_FILE)
    previously_matched['id'] = previously_matched['ref_id']
    return previously_matched


found_delegates = make_previously_matched()

with open(JUNK_JSON, 'r') as rj:
    ekwz = json.load(fp=rj)

def variant2str(variant):
    if type(variant) == str:
        return variant
    else:
        try:
            return variant.form
        except AttributeError:
            pass

def save_db(serializable_df):
    serializable_df.variants = serializable_df.variants.apply(lambda x: [variant2str(n) for n in x])
    serializable_df.to_parquet(PICKLE_FILE_FOUND)

    for interval in ["hypothetical_life", "period_active"]:
        serializable_df[interval]=serializable_df[interval].apply(lambda x: [x.left, x.right])
    serializable_df.to_excel(EXCEL_FILE_FOUND)