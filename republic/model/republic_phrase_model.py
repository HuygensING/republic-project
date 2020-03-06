resolution_categories = {
    "resolution_accepted": [
        "is goedgevonden ende verftaan",
        "IS naar voorgaande deliberatie goedgevonden ende verstaan",
        "de voorfchreve Miffive copielijck overgenomen",
    ],
    "resolution_decision": [
        "gehouden voor gecommiteert",
        "waar by goedgevonden is",
        "voor de genomen moeyte bedanckt", # should probably move somewhere else
    ],
    "resolution_not_accepted": [
        "WAAR op geen refolutie is gevallen",
    ],
    "resolution_opening": [
        "hebben ter Vergaderinge ingebraght",
        "Is ter Vergaderinge gelefen",
        "IS gehoort het rapport van",
        "Ontvangen een Miffive van",
        "Op de Requefte van",
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
        "DE Refolutien, gifteren genomen",
        "zyn gelefen en gerefumeert",
    ],
    "non_meeting_date": [
        "Nihil actum eft.",
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
    "DE Refolutien, gifteren genomen": [
        "DE Refolutien, eergifteren genomen",
    ],
    "Ontvangen een Miffive van": [
        "ON een Miffive van",
        "Ontfangen een Miffive van",
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
    "is goedgevonden ende verftaan": [
        "IS goedgevonden ende verftaan",
        "Is goedgevonden en verftaan",
    ],
    "WAAR op geen refolutie is gevallen": [
        "Waer op geen refolutie is gevallen",
        "WAAR op geen refolutie voor alsnoch is gevallen",
        "Waer op geen refolutie voor alsnoch is gevallen",
    ]
}

