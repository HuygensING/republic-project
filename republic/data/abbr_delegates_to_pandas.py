import os
import ast

import pandas as pd

from republic.helper.utils import get_project_dir

project_dir = get_project_dir()
DATA_DIR = os.path.join(project_dir, 'republic/data')


def abbreviated_delegates_from_excel(save=True):
    pickle_file = os.path.join(DATA_DIR, 'csvs/abbreviated_delegates.pickle')
    excel_file = os.path.join(DATA_DIR, 'csvs/abbreviated_delegates.xlsx')
    abbreviated_delegates = pd.read_excel(excel_file)
    abbreviated_delegates.drop([c for c in abbreviated_delegates.columns if 'Unnamed' in c], axis=1, inplace=True)
    abbreviated_delegates['geboortejaar'] = abbreviated_delegates.geboortejaar.apply(lambda x: pd.Period(x, freq="D"))
    abbreviated_delegates['overlijdensjaar'] = abbreviated_delegates.sterfjaar.apply(lambda x: pd.Period(x, freq="D"))
    for interval in ['h_life', 'p_interval']:
        ni = abbreviated_delegates[interval].apply(lambda x: ast.literal_eval(x))
        nii = ni.apply(lambda x: pd.Interval(int(x[0]), int(x[1]), closed='both'))
        abbreviated_delegates[interval] = nii
    #abbreviated_delegates['period'] = abbreviated_delegates['p_interval'].apply(lambda x: pd.PeriodIndex([f"01-01-{x.left}",f"31-12-{x.right}"], freq="D"))
    if save is True:
        abbreviated_delegates.to_parquet(pickle_file)
    return abbreviated_delegates
