import pandas as pd
import pkg_resources

PICKLE_FILE = pkg_resources.resource_filename(__name__, 'csvs/gedeputeerden_uitgebreid.pickle')
EXCEL_FILE = pkg_resources.resource_filename(__name__, 'csvs/gedeputeerden_uitgebreid.xlsx')


def hypothetical_life(x):  # x is row from dataframe, but I don't know how to declare the type
    if x.geboortejaar == x.geboortejaar: # awful hack depending on NaN not being equal to itself
        gj = x["geboortejaar"].year
    else:
        if x.was_gedeputeerde == True:
            gj = x.p_interval.left - 44
        else:
            gj = x.p_interval.left - 34
    if x.sterfjaar == x.sterfjaar and x.sterfjaar.year >= gj:
        sj = x.sterfjaar.year
    else:
        sj = x.p_interval.right + 22
    try:
        rjinterval = pd.Interval(gj, sj, closed="both")
        return rjinterval
    except ValueError:
        # errors in the database
        print(x.id, gj, sj)

def ptoy(p):
    mn = p.min().year
    if pd.isna(mn):
        mn = 0
    mx = p.max().year or 0
    if pd.isna(mx):
        mx = 0
    i1 = pd.Interval(int(mn), int(mx), closed='both')
    return i1

def maxmin(x):
    name = x.regent.min() # this is the same as max, but what the f**k
    mn = x.van_p.min()
    mx = x.tot_p.max()
    if not mn == mn:
        mn = mx - 365
    if not mx == mx:
        mx = mn + 365

#     try:
#         period = pd.period_range(mn, mx, freq="D")
#     except ValueError:
#         period = pd
    try:
        period = pd.period_range(mn, mx)
        result = pd.Series({'name': name,  'DayMin': mn, 'DayMax': mx, 'period':period})
    except:
        result = pd.NaT
    return result


def make_abbreviated_delegates():
    try:
        df = pd.read_pickle(PICKLE_FILE)
    except (IOError, TypeError):
        df = pd.read_excel(EXCEL_FILE)
        df['van_p'] = df.van.apply(lambda x: pd.Period(x, freq="D")) # this should be possible with to_period, but gives an error
        df['tot_p'] = df.tot.apply(lambda x: pd.Period(x, freq="D"))
        df['geboortedatum_p'] = df.geboortedatum.apply(lambda x: pd.Period(x, freq="D"))
        df['overlijdensdatum_p'] = df.overlijdensdatum.apply(lambda x: pd.Period(x, freq="D"))
    grouped = df.groupby('persoon_id')
    grouped.apply(maxmin)
    unique_ids = grouped.groups.keys()
    records = []
    for id in unique_ids:
        rec = df.loc[df.persoon_id==id]
        mn = rec.van_p.min()
        mx = rec.tot_p.max()
        if not mn == mn:
            mn = mx - 365
        if not mx == mx:
            mx = mn + 365

        period = pd.period_range(start=mn, end=mx, freq="D")

        name = rec.regent.iat[0]
        geboortejaar = rec.geboortedatum_p.iat[0]
        sterfjaar = rec.overlijdensdatum_p.iat[0]
        colleges = ', '.join(list(rec.college.unique()))
        functions = ', '.join(list(rec.functienaam.unique()))
        sg = df.loc[df.college.str.contains('Staten-Generaal der Ve')]
        sg_grouped = sg.groupby('persoon_id')
        sg_grouped.apply(maxmin)
        sg_unique_ids = sg_grouped.groups.keys()
        if id in sg_unique_ids: # getting rid of second dataframe
            sg = True
        else:
            sg = False
        gedeputeerde = False
        if len(rec.loc[rec.college.str.contains('Staten-Generaal der Ve') & rec.functienaam.str.contains('gedeputeerde')]) > 0:
            gedeputeerde = True
        record = {"id":id,
                  "name":name,
                  "geboortejaar":geboortejaar,
                  "sterfjaar":sterfjaar,
                  "colleges":colleges,
                  "functions":functions,
                  "period":period,
                  "sg": sg,
                  "was_gedeputeerde": gedeputeerde}
        records.append(record)
        abbreviated_df = pd.DataFrame(records)
        abbreviated_df['p_interval'] = abbreviated_df.period.apply(lambda x: ptoy(x))
        #abbreviated_df.loc[(~abbreviated_df.sterfjaar.dt.year.isna()) & (abbreviated_df.sterfjaar != 0.0)]
        return abbreviated_df


