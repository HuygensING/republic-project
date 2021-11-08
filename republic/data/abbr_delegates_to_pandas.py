import pandas as pd
import ast
import pkg_resources

EXCEL_FILE = pkg_resources.resource_filename(__name__, 'csvs/abbreviated_delegates.xlsx')
PICKLE_FILE = pkg_resources.resource_filename(__name__, 'csvs/abbreviated_delegates.pickle')

def abbreviated_delegates_from_excel(save=True):
    abbreviated_delegates = pd.read_excel(EXCEL_FILE)
    abbreviated_delegates.drop([c for c in abbreviated_delegates.columns if 'Unnamed' in c], axis=1, inplace=True)
    abbreviated_delegates['geboortejaar'] = abbreviated_delegates.geboortejaar.apply(lambda x: pd.Period(x, freq="D"))
    abbreviated_delegates['overlijdensjaar'] = abbreviated_delegates.sterfjaar.apply(lambda x: pd.Period(x, freq="D"))
    for interval in ['h_life', 'p_interval']:
        ni = abbreviated_delegates[interval].apply(lambda x: ast.literal_eval(x))
        nii = ni.apply(lambda x: pd.Interval(int(x[0]), int(x[1]), closed='both'))
        abbreviated_delegates[interval] = nii
    #abbreviated_delegates['period'] = abbreviated_delegates['p_interval'].apply(lambda x: pd.PeriodIndex([f"01-01-{x.left}",f"31-12-{x.right}"], freq="D"))
    if save is True:
        abbreviated_delegates.to_pickle(PICKLE_FILE)
    return abbreviated_delegates
