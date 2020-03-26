resolution_categories = {
    "resolution_accepted": [
        "is goedgevonden ende verstaan",
        "IS naar voorgaande deliberatie goedgevonden ende verstaan",
        "de voorfchreve Missive copielijck overgenomen",
    ],
    "resolution_decision": [
        "gehouden voor gecommiteert",
        "waar by goedgevonden is",
        "voor de genomen moeyte bedanckt", # should probably move somewhere else
    ],
    "resolution_not_accepted": [
        "WAAR op geen resolutie is gevallen",
    ],
    "resolution_opening": [
        "hebben ter Vergaderinge ingebraght",
        "Is ter Vergaderinge gelesen",
        "IS gehoort het rapport van",
        "Ontvangen een Missive van",
        "Op de Requeste van",
        "Zynde ter Vergaderinge getoont",
    ],
    "resolution_considered": [
        "WAAR op gedelibereert en in achtinge genomen zynde",
        "WAAR op gedelibereert zijnde",
        "WAAR op gedelibereert",
    ],
    "resolution_resumed": [
        "BY refumptie gedelibereert zynde",
    ],
    "resolution_summarized": [
        "DE Resolutien, gisteren genomen",
        "zyn gelesen en gerefumeert",
    ],
    "non_meeting_date": [
        "Nihil actum est.",
    ],
    "resolution_first_entry": [
        "Zynde Nieuwejaarsdagh",
    ],
    "participant_list": [
        "PRAESIDE",
        "PRAESENTIBUS",
    ],
}

category_index = {phrase: category for category in resolution_categories for phrase in resolution_categories[category]}

resolution_phrases = [phrase for category in resolution_categories for phrase in resolution_categories[category]]

participant_list_phrases = [
    "PRAESIDE",
    "PRAESENTIBUS",
]

week_day_names = [
    "Lunae",
    "Martis",
    "Mercurii",
    "Jovis",
    "Veneris",
    "Sabbathi",
    "Dominica"
]

month_names_early = [
    "Januarii",
    "Februarii",
    "Maart",
    "April",
    "Mey",
    "Junii",
    "Juli",
    "Augufti",
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
    "Augufty",
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

keywords = resolution_phrases

spelling_variants = {
    "WAAR op gedelibereert zijnde": [
        "Waer op gedelibereert zynde"
    ],
    "DE Resolutien, gisteren genomen": [
        "DE Resolutien, eergisteren genomen",
    ],
    "Ontvangen een Missive van": [
        "ON een Missive van",
        "Ontfangen een Missive van",
        "Ontfangen twee Missiven van"
    ],
    "PRAESENTIBUS": [
        "PRASENTIBUS",
        "PRESENTIBUS",
        "P R A S E N T I B U S",
        "P R E S E N T I B U S"
    ],
    "PRAESIDE": [
        "PRASIDE",
        "PRESIDE",
        "P R A S I D E",
        "P R E S I D E"
    ],
    "is goedgevonden ende verstaan": [
        "IS goedgevonden ende verstaan",
        "Is goedgevonden en verstaan",
    ],
    "WAAR op geen resolutie is gevallen": [
        "Waer op geen resolutie is gevallen",
        "WAAR op geen resolutie voor alsnoch is gevallen",
        "Waer op geen resolutie voor alsnoch is gevallen",
    ]
}

meeting_phrase_model = [
    {
        'keyword': 'Extract uyt de Resolutien',
        'start_year': 1703, 'end_year': 1796,
        'label': 'extract',
        'variants': [
            'Extract uyt het Resolutie-',
            'Extract uyt het Register',
            'Extraheert uyt het Re-'
        ]
    },
    {
        'keyword': 'Het eerste jaar der Bataafsche Vryheid',
        'start_year': 1795, 'end_year': 1796,
        'label': 'tagline'
    },
    {
        'keyword': 'Nihil actum est',
        'start_year': 1703, 'end_year': 1796,
        'label': 'rest_day'
    },
    {
        'keyword': 'Zynde Vast- en Bede-dag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
    },
    {
        'keyword': 'GECOMPAREERT,',
        'start_year': 1703, 'end_year': 1796,
        'label': 'special_attendance'
    },
    {
        'keyword': 'PRAESIDE,',
        'variants': ['P R AE S I D E,'],
        'start_year': 1703, 'end_year': 1796,
        'label': 'presiding'
    },
    {
        'keyword': 'PRAESENTIBUS,',
        'variants': ['P R AE S E N T I B U S,'],
        'start_year': 1703, 'end_year': 1796,
        'label': 'attending'
    },
    {
        'keyword': 'Den Heere',
        'variants': ['De Heer'],
        'start_year': 1703, 'end_year': 1796,
        'label': 'president'
    },
    {
        'keyword': 'De Heeren',
        'start_year': 1703, 'end_year': 1796,
        'label': 'attendants'
    },
    {
        'keyword': 'Den Burger',
        'start_year': 1795, 'end_year': 1796,
        'label': 'president'
    },
    {
        'keyword': 'De Burgers',
        'start_year': 1795, 'end_year': 1796,
        'label': 'attendants'
    },
    {
        'keyword': 'DE Resolutien gisteren genomen',
        'variants': [
            'DE Resolutien eergisteren genomen',
            'DE Resolutien voorleede ',
            'DE Resolutien gisteren ge-',
        ],
        'start_year': 1703, 'end_year': 1796,
        'label': 'reviewed'
    },
]

extra_phrases = [
    {
        'keyword': 'Zyne Hoogheid den Heere Prince van Orange en Nassau',
        'label': 'prince',
        'start_year': 1703, 'end_year': 1796,
        'line_type': 'multi_line',
        'max_offset': 4
    }
]

holiday_phrases = [
    {
        'keyword': 'Zynde Nieuwjaarsdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': True
    },
    {
        'keyword': 'Zynde Vast- en Bede-dag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'keyword': 'Zynde eerste Paasdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'keyword': 'Zynde tweede Paasdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'keyword': 'Zynde Hemelvaartsdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'keyword': 'Zynde tweede Pinksterdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': False
    },
    {
        'keyword': 'Zynde eerste Kerstdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': True
    },
    {
        'keyword': 'Zynde tweede Kerstdag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'date_specifc': True
    },
]

resolution_phrase_model = [
    {
        'keyword': 'Is ter Vergaderinge gelesen',
        'label': 'resolution_opening',
    },
    {
        'keyword': 'Ontfangen een Missive van',
        'label': 'resolution_opening',
        'resolution_source': 'missive',
    },
    {
        'keyword': 'Is gehoort het rapport van',
        'label': 'resolution_opening',
        'resolution_source': 'rapport',
    },
    {
        'keyword': 'Op de Requeste van',
        'label': 'resolution_opening',
        'resolution_source': 'request',
    },
    {
        'keyword': 'Op de Memorie van',
        'label': 'resolution_opening',
        'resolution_source': 'memorie',
    },
]

