resolution_categories = {
    "resolution_accepted": [
        "is goedgevonden ende verstaan",
        "IS naar voorgaande deliberatie goedgevonden ende verstaan",
        "de voorfchreve Missive copielijck overgenomen",
    ],
    "resolution_decision": [
        "gehouden voor gecommiteert",
        "waar by goedgevonden is",
        "voor de genomen moeyte bedanckt",
        # should probably move somewhere else
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

session_phrase_model = [
    {
        'phrase': 'geinsereert.',
        'start_year': 1585, 'end_year': 1796,
        'label': 'insertion'
    },
    {
        'phrase': 'Extract uyt de Resolutien',
        'start_year': 1603, 'end_year': 1796,
        'label': 'extract',
        'variants': [
            'Extract uyt het Resolutie-',
            'Extract uyt het Register',
            'Extraheert uyt het Re-'
        ]
    },
    {
        'phrase': 'Het eerste jaar der Bataafsche Vryheid',
        'start_year': 1795, 'end_year': 1796,
        'label': 'tagline'
    },
    {
        'phrase': 'Nihil actum est',
        'start_year': 1603, 'end_year': 1796,
        'label': 'rest_day'
    },
    {
        'phrase': 'Zynde Vast- en Bede-dag',
        'start_year': 1703, 'end_year': 1796,
        'label': 'holiday',
        'variants': [
            'Zynde Danck-, Vast- en Bededagh'
        ]
    },
    {
        'phrase': 'GECOMPAREERT,',
        'start_year': 1703, 'end_year': 1796,
        'label': 'special_attendance'
    },
    {
        'phrase': 'Zyne Hoogheid den Heere Prince van ',
        'label': 'prince_attending',
        'start_year': 1703, 'end_year': 1796,
        'line_type': 'multi_line',
        'variants': [
            'Syne Hoogheyd den Heere Prince van ',
        ],
    },
    {
        'phrase': 'Præside,',
        'variants': ['Praeside'],
        'start_year': 1603, 'end_year': 1680,
        'label': 'presiding'
    },
    {
        'phrase': 'Præsentibus,',
        'variants': ['praesentibus'],
        'start_year': 1603, 'end_year': 1680,
        'label': 'attending'
    },
    {
        'phrase': 'PRAESIDE,',
        'variants': ['P R AE S I D E,'],
        'start_year': 1703, 'end_year': 1796,
        'label': 'presiding'
    },
    {
        'phrase': 'PRAESENTIBUS,',
        'variants': ['P R AE S E N T I B U S,'],
        'start_year': 1703, 'end_year': 1796,
        'label': 'attending'
    },
    {
        'phrase': 'Den Heere',
        'variants': ['De Heer'],
        'start_year': 1603, 'end_year': 1796,
        'label': 'president'
    },
    {
        'phrase': 'De Heeren',
        'start_year': 1603, 'end_year': 1796,
        'label': 'attendants'
    },
    {
        'phrase': 'Den Burger',
        'start_year': 1795, 'end_year': 1796,
        'label': 'president'
    },
    {
        'phrase': 'De Burgers',
        'start_year': 1795, 'end_year': 1796,
        'label': 'attendants'
    },
    {
        'phrase': 'DE Resolutien gisteren genomen',
        'variants': [
            'DE Resolutien eergisteren genomen',
            'DE Resolutien voorleede ',
            'DE Resolutien gisteren ge-',
        ],
        'start_year': 1705, 'end_year': 1796,
        'label': 'reviewed'
    },
    {
        'phrase': 'De resolutien gisteren genomen',
        'variants': [
            'De resolutien eergisteren genomen',
            'De resolutien voorleden ',
            'De resolutien gisteren ge-',
        ],
        'start_year': 1603, 'end_year': 1704,
        'label': 'reviewed'
    },
]

extra_phrases = [
    {
        'phrase': 'Zyne Hoogheid den Heere Prince van ',
        'label': 'prince_attending',
        'start_year': 1703, 'end_year': 1796,
        'line_type': 'multi_line',
        'variants': [
            'Syne Hoogheyd den Heere Prince van ',
        ],
        'max_offset': 4
    }
]

resolution_phrase_model = [
    {
        'phrase': 'hebben ter Vergaderinge ingebraght',
        'label': 'resolution_opening',
        'variants': [
            'heeft ter Vergaderinge ingebraght',
        ]
    },
    {
        'phrase': 'Zynde ter Vergaderinge getoont',
        'label': 'resolution_opening',
        'max_offset': 4
    },
    {
        'phrase': 'Is ter Vergaderinge gelesen',
        'label': 'resolution_opening',
        'max_offset': 4
    },
    {
        'phrase': 'Ontfangen een Missive van',
        'label': 'resolution_opening',
        'resolution_source': 'missive',
        'variants': [
            'ON een Missive van',
            'ONtfangen een Miffive van',
            'Nogh ontfangen een Missive van'
        ],
        'max_offset': 4
    },
    {
        'phrase': 'Is gehoort het rapport van',
        'label': 'resolution_opening',
        'resolution_source': 'rapport',
        'max_offset': 4
    },
    {
        'phrase': 'Op de Requeste van',
        'label': 'resolution_opening',
        'resolution_source': 'request',
        'max_offset': 4
    },
    {
        'phrase': 'Op de Memorie van',
        'label': 'resolution_opening',
        'resolution_source': 'memorie',
        'max_offset': 4
    },
    {
        'phrase': 'Op het gerapporteerde van de Heeren van',
        'label': 'resolution_opening',
        'resolution_source': 'rapport',
        'max_offset': 4
    },
    {
        'phrase': 'heeft aan haar Hoogh Mogende voorgedraagen en bekend gemaackt',
        'variants': [
            'hebben aan haar Hoogh Mogende voorgedraagen en bekend gemaackt'
        ],
        'label': 'resolution_opening',
        'max_offset': 100
    },
    {
        'phrase': 'is goedgevonden ende verstaan',
        'label': 'resolution_decision',
        'variants': [
            "IS naar voorgaande deliberatie goedgevonden ende verstaan",
        ]
    },
    {
        'phrase': 'de voorfchreve Missive copielijck overgenomen',
        'label': 'resolution_decision',
    },
    {
        'phrase': 'waar by goedgevonden is',
        'label': 'resolution_decision',
    },
    {
        'phrase': 'gehouden voor gecommiteert',
        'label': 'resolution_decision',
    },
    {
        'phrase': 'WAAR op gedelibereert en in achtinge genomen zynde',
        'label': 'resolution_decision',
    },
    {
        'phrase': 'WAAR op gedelibereert zijnde',
        'label': 'resolution_decision',
    },
    {
        'phrase': 'WAAR op gedelibereert',
        'label': 'resolution_decision',
    },
    {
        'phrase': 'voor de genomen moeyte bedanckt',  # should probably move somewhere else
        'label': 'resolution_decision',
    },
    {
        'phrase': 'WAAR op geen resolutie is gevallen',
        'variants': [
            "Waer op geen resolutie is gevallen",
            "WAAR op geen resolutie voor alsnoch is gevallen",
            "Waer op geen resolutie voor alsnoch is gevallen",
        ],
        'label': 'resolution_decision',
    },
    {
        'phrase': 'BY refumptie gedelibereert zynde',
        'label': 'resolution_opening',
        'max_offset': 4
    },
    {
        'phrase': 'DE Resolutien, gisteren genomen',
        'label': 'resolution_summarized',
        'max_offset': 4,
        'variants': [
            'DE Resolutien, eergisteren genomen',
            'DE Resolutien voorleede ',
        ]
    },
    {
        'phrase': 'zyn gelesen en gerefumeert',
        'label': 'resolution_summarized'
    },
]
