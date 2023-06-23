from collections import defaultdict

from republic.model.inventory_mapping import get_inventory_by_num
from republic.model.inventory_mapping import get_inventory_by_id


week_day_names_handwritten = [
    "Lunæ",
    "Martis",
    "Mercurii",
    "Jovis",
    "Veneris",
    "Sabbathi",
    "Dominica"
]

week_day_names_printed = [
    "Lunae",
    "Martis",
    "Mercurii",
    "Jovis",
    "Veneris",
    "Sabbathi",
    "Dominica"
]


month_day_names = {
    'roman_early': {
        'eerste': 1,
        'Prima': 1,
        'je': 1,
        'ije': 2,
        'Secunda': 2,
        'iije': 3,
        'Tertia': 3,
        'iiije': 4,
        'Quarta': 4,
        've': 5,
        'vje': 6,
        'vie': 6,
        'vije': 7,
        'viie': 7,
        'viije': 8,
        'ixe': 9,
        '1xe': 9,
        'xe': 10,
        'xje': 11,
        'xie': 11,
        'xije': 12,
        'xiie': 12,
        'xiije': 13,
        'xiiije': 14,
        'xve': 15,
        'xvje': 16,
        'xvie': 16,
        'xvije': 17,
        'xviie': 17,
        'xviije': 18,
        'xixe': 19,
        'xxe': 20,
        'xxje': 21,
        'xxie': 21,
        'xxije': 22,
        'xxiie': 22,
        'xxiije': 23,
        'xxiiije': 24,
        'xxve': 25,
        'xxvje': 26,
        'xxvie': 26,
        'xxvije': 27,
        'xxviie': 27,
        'xxviije': 28,
        'xxixe': 29,
        'xxxe': 30,
        'xxxie': 30,
        'leste': 0,
        'laeste': 0,
        'Laeste': 0,
        'naestleste': -1,
        'naleste': -1
    },
    'roman_en': {
        'eersten': 1,
        'jen': 1,
        'ijen': 2,
        'iijen': 3,
        'iiijen': 4,
        'ven': 5,
        'vjen': 6,
        'vien': 6,
        'vijen': 7,
        'viien': 7,
        'viijen': 8,
        'ixen': 9,
        '1xen': 9,
        'xen': 10,
        'xjen': 11,
        'xien': 11,
        'xijen': 12,
        'xiien': 12,
        'xiijen': 13,
        'xiiijen': 14,
        'xven': 15,
        'xvjen': 16,
        'xvien': 16,
        'xvijen': 17,
        'xviien': 17,
        'xviijen': 18,
        'xixen': 19,
        'xxen': 20,
        'xxjen': 21,
        'xxien': 21,
        'xxijen': 22,
        'xxiien': 22,
        'xxiijen': 23,
        'xxiiijen': 24,
        'xxven': 25,
        'xxvjen': 26,
        'xxvien': 26,
        'xxvijen': 27,
        'xxviien': 27,
        'xxviijen': 28,
        'xxixen': 29,
        'xxxen': 30,
        'xxxien': 30,
        'lesten': 0,
        'laesten': 0,
        'Laesten': 0,
        'naestlesten': -1,
        'nalesten': -1
    },
    'decimal_dot': {
        '1.': 1,
        '2.': 2,
        '3.': 3,
        '4.': 4,
        '5.': 5,
        '6.': 6,
        '7.': 7,
        '8.': 8,
        '9.': 9,
        '10.': 10,
        '11.': 11,
        '12.': 12,
        '13.': 13,
        '14.': 14,
        '15.': 15,
        '16.': 16,
        '17.': 17,
        '18.': 18,
        '19.': 19,
        '20.': 20,
        '21.': 21,
        '22.': 22,
        '23.': 23,
        '24.': 24,
        '25.': 25,
        '26.': 26,
        '27.': 27,
        '28.': 28,
        '29.': 29,
        '30.': 30,
        '31.': 31
    },
    'decimal_en': {
        '1en': 1,
        '2en': 2,
        '3en': 3,
        '4en': 4,
        '5en': 5,
        '6en': 6,
        '7en': 7,
        '8en': 8,
        '9en': 9,
        '10en': 10,
        '11en': 11,
        '12en': 12,
        '13en': 13,
        '14en': 14,
        '15en': 15,
        '16en': 16,
        '17en': 17,
        '18en': 18,
        '19en': 19,
        '20en': 20,
        '21en': 21,
        '22en': 22,
        '23en': 23,
        '24en': 24,
        '25en': 25,
        '26en': 26,
        '27en': 27,
        '28en': 28,
        '29en': 29,
        '30en': 30,
        '31en': 31
    },
    'decimal_en_dot': {
        '1en.': 1,
        '2en.': 2,
        '3en.': 3,
        '4en.': 4,
        '5en.': 5,
        '6en.': 6,
        '7en.': 7,
        '8en.': 8,
        '9en.': 9,
        '10en.': 10,
        '11en.': 11,
        '12en.': 12,
        '13en.': 13,
        '14en.': 14,
        '15en.': 15,
        '16en.': 16,
        '17en.': 17,
        '18en.': 18,
        '19en.': 19,
        '20en.': 20,
        '21en.': 21,
        '22en.': 22,
        '23en.': 23,
        '24en.': 24,
        '25en.': 25,
        '26en.': 26,
        '27en.': 27,
        '28en.': 28,
        '29en.': 29,
        '30en.': 30,
        '31en.': 31
    }
}

month_names = {
    'printed_early': {
        'Januarij': 1,
        'Februarij': 2,
        'Maart': 3,
        'April': 4,
        'Mey': 5,
        'Junij': 6,
        'Julij': 7,
        'Augusti': 8,
        'September': 9,
        'October': 10,
        'November': 11,
        'December': 12
    },
    'printed_late': {
        'January': 1,
        'February': 2,
        'Maart': 3,
        'April': 4,
        'Mey': 5,
        'Juny': 6,
        'July': 7,
        'Augusti': 8,
        'September': 9,
        'October': 10,
        'November': 11,
        'December': 12
    },
    'handwritten': {
        'January': 1,
        'Januarij': 1,
        'February': 2,
        'Februarij': 2,
        'Meerte': 3,
        'Martij': 3,
        'Marty': 3,
        'Meert': 3,
        'Aprilis': 4,
        'April': 4,
        'Maij': 5,
        'May': 5,
        'Mey': 5,
        'Meije': 5,
        'Meye': 5,
        'Maye': 5,
        'Junij': 6,
        'Juny': 6,
        'Julij': 7,
        'July': 7,
        'Augusti': 8,
        'Septembris': 9,
        'Septemb': 9,
        'September': 9,
        'Octobris': 10,
        'Octob': 10,
        'Novembris': 11,
        'Novemb': 11,
        'Decembris': 12,
        'Decemb': 12,
        'December': 12
    }
}

week_day_names = {
    'printed_early': {
        "Lunae": 0,
        "Martis": 1,
        "Mercurii": 2,
        "Jovis": 3,
        "Veneris": 4,
        "Sabbathi": 5,
        "Dominica": 6
    },
    'printed_late': {
        "Lunae": 0,
        "Martis": 1,
        "Mercurii": 2,
        "Jovis": 3,
        "Veneris": 4,
        "Sabbathi": 5,
        "Dominica": 6
    },
    'handwritten': {
        "Lunae": 0,
        "Luna": 0,
        "Martis": 1,
        "Mercurij": 2,
        "Mercury": 2,
        "Jovis": 3,
        "Veneris": 4,
        "Sabbathi": 5,
        "Saterdach": 5,
        "Dominica": 6,
        "Sondach": 6
    }
}

date_name_map = [
    {
        'text_type': 'printed_early',
        'resolution_type': 'ordinaris',
        'period_start': 1705,
        'period_end': 1750,
        'month_name': month_names['printed_early'],
        'week_day_name': week_day_names['printed_early']
    },
    {
        'text_type': 'printed_late',
        'resolution_type': 'ordinaris',
        'period_start': 1751,
        'period_end': 1796,
        'month_name': month_names['printed_late'],
        'week_day_name': week_day_names['printed_late']
    },
    {
        'text_type': 'handwritten',
        'resolution_type': 'secreet',
        'period_start': 1600,
        'period_end': 1700,
        'month_name': month_names['handwritten'],
        'week_day_name': week_day_names['handwritten']
    },
    {
        'text_type': 'handwritten',
        'resolution_type': 'ordinaris',
        'period_start': 1587,
        'period_end': 1599,
        'month_name': month_names['handwritten'],
        'week_day_name': week_day_names['handwritten'],
        'month_day_name': month_day_names['roman_early']
    },
    {
        'text_type': 'handwritten',
        'resolution_type': 'ordinaris',
        'period_start': 1600,
        'period_end': 1655,
        'month_name': month_names['handwritten'],
        'week_day_name': week_day_names['handwritten'],
        'month_day_name': month_day_names['roman_en']
    },
    {
        'text_type': 'handwritten',
        'resolution_type': 'ordinaris',
        'period_start': 1656,
        'period_end': 1700,
        'month_name': month_names['handwritten'],
        'week_day_name': week_day_names['handwritten'],
        'month_day_name': month_day_names['decimal_en']
    }
]

month_names_early = [
    "Januarii",
    "Februarii",
    "Maart",
    "April",
    "Mey",
    "Junii",
    "Juli",
    "Augusti",
    "September",
    "October",
    "November",
    "December"
]

month_names_late = [
    "January",
    "February",
    "Maart",
    "April",
    "Mey",
    "Juny",
    "July",
    "Augusty",
    "September",
    "October",
    "November",
    "December"
]

week_day_name_map = {
    "Lunae": 1,
    "Martis": 2,
    "Mercurii": 3,
    "Jovis": 4,
    "Veneris": 5,
    "Sabbathi": 6,
    "Dominica": 7
}

month_map_early = {
    "Januarii": 1,
    "Februarii": 2,
    "Maart": 3,
    "April": 4,
    "Mey": 5,
    "Junii": 6,
    "Juli": 7,
    "Augufti": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}

month_map_late = {
    "January": 1,
    "February": 2,
    "Maart": 3,
    "April": 4,
    "Mey": 5,
    "Juny": 6,
    "July": 7,
    "Augufty": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}

holiday_phrases = [
    {
        'phrase': 'Zynde Nieuwjaarsdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': True
    },
    {
        'phrase': 'Zynde Vast- en Bede-dag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'phrase': 'Zynde eerste Paasdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'phrase': 'Zynde tweede Paasdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'phrase': 'Zynde Hemelvaartsdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'phrase': 'Zynde tweede Pinksterdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'phrase': 'Zynde eerste Kerstdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': True
    },
    {
        'phrase': 'Zynde tweede Kerstdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': True
    },
]


def get_date_token_cat(inv_num: int = None, inv_id: str = None):
    if inv_num:
        inv_metadata = get_inventory_by_num(inv_num)
        if inv_metadata is None:
            raise ValueError(f'invalid inv_num {inv_num}')
    elif inv_id:
        inv_metadata = get_inventory_by_id(inv_id)
        if inv_metadata is None:
            raise ValueError(f'invalid inv_id {inv_id}')
    else:
        raise ValueError('need to pass either inv_num or inv_id')
    print(inv_metadata)
    date_token_map = {
        'month_name': month_names,
        'month_day_name': month_day_names,
        'week_day_name': week_day_names,
        'year': [year for year in range(inv_metadata['year_start'], inv_metadata['year_end']+1)]
    }

    date_token_cat = defaultdict(set)

    for name_set in date_token_map:
        for set_version in date_token_map[name_set]:
            for date_token in date_token_map[name_set][set_version]:
                date_token_cat[date_token].add((name_set, set_version))

    return date_token_cat
