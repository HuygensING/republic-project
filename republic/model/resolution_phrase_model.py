keyword_dicts = [
    {
        'phrase': 'de Provincie van Holland en Westvriesland',
        'label': 'province',
        'variants': [
            'de Provincie van Stad en Lande',
            'de Provincie van Gelderland',
            'de Provincie van Zeeland',
            'de Provincie van Utrecht',
            'de Provincie van Overyssel',
            'de Provincie van Vriesland',
        ]
    },
]


proposition_opening_phrases = [
    {
        'phrase': 'ONtfangen een Missive van',
        'label': ['proposition_opening', 'proposition_type:missive'],
        'proposition_type': 'missive',
        'max_offset': 5
    },
    {
        'phrase': 'heeft ter Vergadering gecommuniceert ',
        'label': 'proposition_opening',
        'variants': [
            'heeft ter Vergaderinge ingebraght',
            'heeft ter Vergaderinge voorgedragen',
        ],
        'proposition_type': None,
        'max_offset': 250
    },
    {
        'phrase': 'heeft aan haar Hoog Mog. voorgedragen',
        'label': 'proposition_opening',
        'variants': [
            'heeft aan haar Hoog Mog. ingebraght',
            'heeft aan haar Hoog Mog. gecommuniceert',
        ],
        'proposition_type': None,
        'max_offset': 250
    },
    {
        'phrase': 'hebben ter Vergaderinge ingebraght',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 250
    },
    {
        'phrase': 'hebben ter Vergaderinge voorgedragen',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 250
    },
    {
        'phrase': 'IS ter Vergaderinge gelesen de Requeste van ',
        'label': ['proposition_opening', 'proposition_type:requeste'],
        'distractors': [
            'IS ter Vergaderinge gelesen de Memorie van ',
            'IS ter Vergaderinge gelesen het Advies van ',
        ],
        'proposition_type': 'requeste',
        'max_offset': 5
    },
    {
        'phrase': 'IS ter Vergaderinge gelesen de Memorie van ',
        'label': ['proposition_opening', 'proposition_type:memorie'],
        'distractors': [
            'IS ter Vergaderinge gelesen de Requeste van ',
            'IS ter Vergaderinge gelesen het Advies van ',
        ],
        'proposition_type': 'memorie',
        'max_offset': 5
    },
    {
        'phrase': 'IS ter Vergaderinge gelesen het Advies van ',
        'label': ['proposition_opening', 'proposition_type:advies'],
        'distractors': [
            'IS ter Vergaderinge gelesen de Memorie van ',
            'IS ter Vergaderinge gelesen de Requeste van ',
        ],
        'proposition_type': 'advies',
        'max_offset': 5
    },
    {
        'phrase': 'IS gehoort het rapport van ',
        'label': ['proposition_opening', 'proposition_type:rapport'],
        'proposition_type': 'rapport',
        'max_offset': 5
    },
    {
        'phrase': 'OP de Requeste van ',
        'label': ['proposition_opening', 'proposition_type:requeste'],
        'proposition_type': 'requeste',
        'max_offset': 5
    },
    {
        'phrase': 'ZYnde ter Vergaderinge getoont en geëxhibeert de Declaratie van ',
        'label': ['proposition_opening', 'proposition_type:declaratie'],
        'distractors': [
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Instructie van ',
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Reekening van ',
        ],
        'proposition_type': "declaratie",
        'max_offset': 5
    },
    {
        'phrase': 'ZYnde ter Vergaderinge getoont en geëxhibeert de Instructie van ',
        'label': ['proposition_opening', 'proposition_type:instructie'],
        'distractors': [
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Declaratie van ',
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Reekening van ',
        ],
        'proposition_type': "instructie",
        'max_offset': 5
    },
    {
        'phrase': 'ZYnde ter Vergaderinge getoont en geëxhibeert de Reekening van ',
        'label': ['proposition_opening', 'proposition_type:rekening'],
        'distractors': [
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Declaratie van ',
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Instructie van ',
        ],
        'proposition_type': "rekening",
        'max_offset': 5
    },
    {
        'phrase': 'OP den differente gereezen voor de',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'BY Resumtie gedelibereert zynde',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'DE Conclusie van versoek van',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'OP de Conclusie van versoek om',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'DE Conclusie van Duplicq van',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'OP de Conclusie van Replicq op',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'DE Conclusie van Eisch in Revisie van',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'DE Conclusie van Eisch op de Requeste',
        'label': ['proposition_opening', 'proposition_type:requeste'],
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'OP het gerepresenteerde uit naam van sijn Hoogheid ter Vergaderinge gedaan',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
    {
        'phrase': 'OP het gerepresenteerde ter Vergaderinge gedaan',
        'label': 'proposition_opening',
        'proposition_type': None,
        'max_offset': 5
    },
]

proposition_verbs = [
    {
        'phrase': "versoekende",
        'label': ['proposition_verb', 'request', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "sendende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "houdende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "brengende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "reclameerende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "presenteerende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "appuyeerende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "raakende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "dienende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "berigtende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "kennisse geevende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': 'houdende advertentie.',
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': 'op ordre en ten dienste van',
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': 'sustineeren',
        'label': ['claim_verb', 'claim', 'proposition_body'],
    },

]

proposition_reason_phrases = [
    {
        'phrase': 'weegens Arbeidsloon en Leeverantie',
        'label': ['proposition_reason', 'salary', 'delivery'],
        'variants': [
            'weegens Arbeidsloon en gedaane Leeverantie'
        ]
    },
    {
        'phrase': 'weegens gedaane Leeverantie',
        'label': ['proposition_reason', 'salary', 'delivery']
    },
]

proposition_closing_phrases = [
    {
        "phrase": "volgens en in conformiteit van de ordres van het Land",
        "label": "proposition_closing"
    },
]

decision_phrases = [
    {
        'phrase': 'WAAR op geen resolutie is gevallen.',
        'label': 'no_decision'
    },
    {
        "phrase": "En sal Extract van deese haar Hoog Mogende Resolutie gesonden worden aan",
        "label": "proposition_closing"
    },
    {
        'phrase': 'om te vifsiteeren , examineeren en liquideeren',
        'label': ['decision_phrases', 'examine']
    },
    {
        "phrase": "Zyn deselve gehouden voor geleesen",
        "label": ["proposition_closing", "resolution_decision"]
    },
    {
        "phrase": "IS deselve gehouden voor geleesen",
        "label": ["proposition_closing", "resolution_decision"]
    },
]

resolution_link_phrases = [
    {
        'phrase': 'in gevolge en ter voldoeninge aan',
        'label': ['resolution_relation', 'response', 'fulfil'],
        'variants': [
            'in gevolge en tot voldoeninge van'
        ]
    },
    {
        'phrase': 'Resolutie',
        'label': ['resolution_relation', 'resolution']
    }
]

prefix_phrases = [
    {
        'phrase': 'den Heere',
        'label': 'person_name_prefix',
        'variants': [
            'de Heer',
            'den Heeren',
            'de Heeren'
        ]
    }
]

organisation_phrases = [
    {
        'phrase': 'de Heeren Staaten van de Provincie',
        'label': ['organisation', 'states', 'province'],
        'cardinality': 'multi',
    },
    {
        'phrase': 'Staaten van de Provincie',
        'label': ['organisation', 'province', 'states'],
    },
    {
        'phrase': 'den Raad van Staate',
        'label': ['organisation', 'council_of_states'],
        'cardinality': 'single',
    },
    {
        'phrase': 'de Generaliteits Reekenkamer',
        'label': ['organisation', 'proposer_title'],
        'cardinality': 'single',
    },
    {
        'phrase': 'by den Ryksdag',
        'label': ['organisation', 'german', 'political']
    },
    {
        'phrase': 'de Generaliteit',
        'label': ['organisation', 'generality'],
    },
    {
        'phrase': 'het Collegie ter Admiraliteit',
        'label': ['organisation', 'navy', 'admiralty'],
    },
    {
        'phrase': 'Oostindische Compagnie',
        'label': ['organisation', 'domain:maritime']
    },
    {
        'phrase': 'Westindische Compagnie',
        'label': ['organisation', 'domain:maritime']
    },
    {
        'phrase': 'Hoofdbanke',
        'label': ['organisation', 'domain:church']
    },
    {
        'phrase': 'de Meyerye',
        'label': ['organisation', 'domain:politics']
    },
]

location_phrases = [
    {
        'phrase': 'Weftvriesland en den Noorder Quartiere',
        'label': 'location'
    },
    {
        'phrase': 'Heerlijkheid ',
        'label': 'location_type'
    },
    {
        'phrase': 'Quartiere ',
        'label': 'location_type'
    },
    {
        'phrase': 'Majorie ',
        'label': 'location_type'
    },
    {
        'phrase': 'het Quartier van Peelland',
        'label': 'location'
    },
    {
        'phrase': 'het District van',
        'label': ['district', 'location_relation']
    },
    {
        'phrase': 'den Lande van ',
        'label': ['location_relation']
    },
    {
        'phrase': 'den Colonie van ',
        'label': ['location_relation']
    },
    {
        'phrase': 'de Kamers Griffie',
        'label': ['location', 'office', 'registrars_office'],
    },

]

esteem_titles = [
    {
        'phrase': 'haar Hoog Mogende',
        'label': ['esteem_title', 'organisation_title'],
        'variants': [
            'haar Hoog Mog.',
            'haar Ho. Mo.'
        ]
    },
    {
        'phrase': 'aan het Hof van ',
        'label': ['representation_relation']
    },

    {
        'phrase': 'de Vaart en Handel op de West-indien',
        'label': ['topic', 'topic:trade', 'domain:maritime']
    },
    {
        'phrase': 'tot de saaken van',
        'label': ['topic_prefix']
    },
    {
        'phrase': 'tot de saaken van de Finantie',
        'label': ['topic', 'topic:finance']
    },
    {
        'phrase': 'tot de buitenlandse saaken',
        'label': ['topic', 'topic:foreign_affairs', 'domain:politics', 'department']
    },
]


person_role_phrases = [
    {
        'phrase': 'Quartierschout ',
        'label': ['person_role', 'representative']
    },
    {
        'phrase': 'Burger',
        'label': ['citizen', 'person_role']
    },
    {
        'phrase': 'Inwoonder',
        'label': ['citizen', 'person_role']
    },
    {
        'phrase': 'Suppliant',
        'label': ['resolution_requester', 'person_role']
    },
    {
        'phrase': 'Impetrant',
        'label': ['resolution_claimant', 'person_role']
    },
    {
        'phrase': 'Gedeputeerde',
        'label': ['deputy', 'person_role']
    },
    {
        'phrase': 'sijne Hoogheid',
        'label': ['sovereign', 'person_role', 'title'],
        'variants': [
            'sijne Doorlugtigste Hoogheid'
        ]
    },
    {
        'phrase': 'sijne Majesteit',
        'label': ['sovereign', 'person_role', 'title']
    },
    {
        'phrase': 'den Representant van',
        'label': ['person_role', 'representative', 'representation_relation']
    },
    {
        'phrase': 'den Grave van',
        'label': ['person_role', 'sovereign', 'representation_relation']
    },
    {
        'phrase': 'den Koning van',
        'label': ['person_role', 'sovereign', 'representation_relation']
    },
    {
        'phrase': 'de gesaamenlijke Knegts van',
        'label': ['person_role', 'laborer', 'servant', 'representation_relation']
    },
    {
        'phrase': 'Comptoir Generaal van',
        'label': ['person_role', 'comptoir', 'representation_relation']
    },
    {
        'phrase': 'Comptoir van',
        'label': ['person_role', 'comptoir', 'representation_relation']
    },
    {
        'phrase': 'Gouverneur Generaal',
        'label': ['person_role', 'governor_general'],
    },
    {
        'phrase': 'Generaal Major',
        'label': ['person_role', 'general_major', 'domain:military'],
    },
    {
        'phrase': 'de Kinderen van ',
        'label': ['person_role', 'children', 'domain:family', 'representative_relation'],
    },
    {
        'phrase': 'de Erfgenaamen van ',
        'label': ['person_role', 'heir', 'domain:law', 'representative_relation'],
    },
    {
        'phrase': 'Advocaaten van ',
        'label': ['person_role', 'lawyer', 'domain:law', 'representative_relation'],
    },
    {
        'phrase': 'Stadhouder van ',
        'label': ['person_role', 'stadholder', 'domain:politics', 'representative_relation'],
    },
    {
        'phrase': 'Gecommitteerden uit',
        'label': ['person_role', 'committee', 'representative_relation'],
    },
    {
        'phrase': 'Geinteresseerden in',
        'label': ['person_role', 'stakeholder', 'representative_relation'],
    },
    {
        'phrase': 'den Griffier',
        'label': ['person_role', 'registrar'],
    },
    {
        'phrase': 'Griffier van',
        'label': ['person_role', 'registrar', 'representative_relation'],
    },
    {
        'phrase': 'Commissaris van',
        'label': ['person_role', 'commissary', 'representative', 'political', 'representative_relation'],
    },
    {
        'phrase': 'Consul van',
        'label': ['person_role', 'consul', 'representative', 'political', 'representative_relation'],
    },
    {
        'phrase': 'Consul Generaal van',
        'label': ['person_role', 'consul', 'representative', 'political', 'representative_relation'],
    },
    {
        'phrase': 'Procureur voor',
        'label': ['person_role', 'prosecutor', 'legal', 'representative_relation'],
    },
    {
        'phrase': 'Bisschop te',
        'label': ['person_role', 'bishop', 'church', 'representative_relation'],
    },
    {
        'phrase': 'Capitein ter Zee',
        'label': ['person_role', 'captain', 'captain_at_sea', 'navy', 'maritime'],
        'role': 'captain_at_sea'
    },
    {
        'phrase': 'Capitein van de Burgerye',
        'label': ['person_role', 'captain', 'captain_of_company', 'military'],
        'role': 'captain_of_company'
    },
    {
        'phrase': 'van Balliuw, Burgermeester en Scheepenen',
        'label': ['person_role', 'representative', 'magistrate'],
        'role': 'magistrate_multi'
    },
    {
        'phrase': 'Kamerbewaarder van',
        'label': ['person_role', 'entourage'],
    },
    {
        'phrase': 'extraordinaris',
        'label': ['person_role', 'extra'],
    },
    {
        'phrase': 'Envoyé',
        'label': ['person_role', 'envoy', 'representative'],
    },
    {
        'phrase': 'Plenipotentiaris',
        'label': ['person_role', 'domain:politcs', 'entourage'],
    },
    {
        'phrase': 'den Secretaris',
        'label': ['person_role', 'title', 'secretary', 'representatitve'],
        'cardinality': 'single',
    },
    {
        'phrase': 'den Commissaris',
        'label': ['person_role', 'commissary', 'representatitve'],
        'cardinality': 'single',
    },
    {
        'phrase': 'den Commissaris Generaal',
        'label': ['person_role', 'commissary', 'representatitve'],
        'variants': [
            'den Commis Generaal'
        ],
        'cardinality': 'single',
    },
    {
        'phrase': 'sijne Furstelyke Doorlugtigheid',
        'label': ['person_role'],
        'cardinality': 'single',
        'proposer_type': 'person',
    },
    {
        'phrase': 'ter Vergaderinge praesideerende',
        'label': ['representation_relation', 'person_role', 'presiding']
    },
    {
        'phrase': 'Ambassadeur',
        'label': ['person_role', 'ambassador', 'representative'],
    },
    {
        'phrase': 'Arbeidsman',
        'label': ['person_role', 'laborer'],
    },
    {
        'phrase': 'Timmerman',
        'label': ['person_role', 'laborer', 'builder', 'artisan'],
    },
    {
        'phrase': 'Metselaar',
        'label': ['person_role', 'laborer', 'builder', 'artisan'],
    },
    {
        'phrase': 'Loodgieter',
        'label': ['person_role', 'laborer', 'builder', 'artisan'],
    },
    {
        'phrase': 'Straatmaker',
        'label': ['person_role', 'laborer', 'builder', 'artisan'],
    },
    {
        'phrase': 'Vuurstooker',
        'label': ['person_role', 'laborer', 'job_title'],
    },
    {
        'phrase': 'Magistraat',
        'label': ['person_role', 'magistrate', 'representative'],
    },
    {
        'phrase': 'Minister',
        'label': ['person_role', 'domain:politics', 'minister', 'representative'],
    },
]

military_phrases = [
    {
        'phrase': 'van de Infanterye',
        'label': ['infantry', 'domain:military'],
    },
    {
        'phrase': 'van de Burgerye',
        'label': ['city_watch', 'domain:military'],
    },
]

misc = [
    {
        'phrase': 'Missive',
        'label': ['document', 'document_type:missive'],
    },
    {
        'phrase': 'Bylaage',
        'label': ['document', 'document_type:attachment'],
    },
    {
        'phrase': 'Copie van',
        'label': ['document', 'document_type:copy', 'document_relation'],
    },
    {
        'phrase': 'geschreeven te',
        'label': 'correspondence_from',
    },
    {
        'phrase': 'geschreeven alhier in Den Hage',
        'label': ['correspondence_from', 'the_hague'],
        'variants': [
            'geschreven - alhier in Den Hage'
        ]
    },
    {
        'phrase': 'woonende te',
        'label': ['resident_in', 'residence_relation'],
        'variants': [
            'resideerende te'
        ],
        'distractors': [
            'wordende met'
        ]
    },
    {
        'phrase': 'woonende alhier in den Hage',
        'label': ['resident_in', 'residence_relation', 'the_hague'],
        'variants': [
            'resideerende alhier in den Hage'
        ],
    },
    {
        'phrase': 'bevindende hier te Lande',
        'label': ['currently_in_republic', 'person_location', 'location:dutch_republic'],
        'variants': [
            'resideerende alhier in den Hage'
        ],
    },
    {
        'phrase': 'den 1 deeser loopende maand',
        'label': ['current_month', 'temporal_reference'],
        'variants': [
            'den 1 en 2 deeser loopende maand'
        ]
    },
    {
        'phrase': 'den .. der voorleeden maand',
        'label': ['previous_month', 'temporal_reference'],
        'variants': [
            'den 1 en 2 der voorleeden maand'
        ]
    },
    {
        'phrase': 'den 1 Januari laatstleden',
        'label': ['previous_named_month', 'temporal_reference'],
        'variants': [
            'den 1 Maart laatstleden',
            'den 1 April laatstleden',
            'den 1 Mei laatstleden',
            'den 1 Juni laatstleden',
            'den 1 Augustus laatstleden',
            'den 1 November laatstleden',
        ]
    },
    {
        'phrase': 'geaddreffeert aan ',
        'label': 'addressed_to'
    },
    {
        'phrase': "'s Lands Oorlogschip",
        'label': ['ship', 'ship_type', 'domain:maritime']
    },
    {
        'phrase': "een Nieuwejaars-Gifte van",
        'label': ['topic', 'domain:finance', 'topic:gift'],
        'variants': [
            "de gewoonlijke Nieuwejaars-Gifte van",
        ]
    },

]

provinces = [
    {
        'phrase': ' van Holland en Westvriesland',
        'label': 'of_province'
    },
    {
        'phrase': ' van Stad en Lande',
        'label': 'of_province'
    },
    {
        'phrase': ' van Gelderland',
        'label': 'of_province'
    },
    {
        'phrase': ' van Zeeland',
        'label': 'of_province'
    },
    {
        'phrase': ' van Utrecht',
        'label': 'of_province'
    },
    {
        'phrase': ' van Overyssel',
        'label': 'of_province'
    },
    {
        'phrase': ' van Vriesland',
        'label': 'of_province'
    },
]

opening_formulas = [
    {
        'elements': ['proposition_opening', 'proposer_title', 'proposer_name', 'esteemed'],
        'variable': ['proposer_name']
    },
    {
        'elements': ['proposition_opening', 'proposer_title', 'proposer_name', 'written_in_location'],
        'variable': ['proposer_name']
    },
    {
        'elements': ['proposition_opening', 'proposer_name', 'person_role', 'organisation'],
        'variable': ['proposer_name']
    },
    {
        'elements': ['proposition_opening', 'proposer_title', 'proposer_title', 'proposer_name', 'written_in_location'],
        'variable': ['proposer_name']
    },

]

opening_templates = [
    {
        "label": "proposition_opening",
        "ordered": True,
        "type": "group",
        "elements": [
            {
                "label": "formula",
                "type": "group",
                "elements": [
                    {"label": "proposition_opening", "required": True},
                ]
            },
            {
                "label": "proposer",
                "type": "group",
                "ordered": False,
                "elements": [
                    {"label": "title", "required": False, "cardinality": "multi"},
                    {"label": "proposer_name", "required": False, "variable": True},
                    {"label": "person_role", "required": False, "cardinality": "multi"},
                    {"label": "representation_relation", "required": False},
                    {"label": "organisation", "required": False},
                ]
            },
            {
                "label": "proposition_origin",
                "type": "group",
                "ordered": True,
                "elements": [
                    {"label": "correspondence_from", "required": False},
                    {"label": "residence_relation", "required": False},
                    {"label": "location", "required": False, "variable": True},
                    {"label": "temporal_reference", "required": False},
                ]
            },
            {
                "label": "proposition_verb",
                "type": "group",
                "elements": [
                    {"label": "proposition_verb", "required": False},
                ]
            }
        ]
    }
]
