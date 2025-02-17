import json


def read_republic_term_dict(dict_file: str = None):
    """Read a JSON formatted term dictionary from file"""
    if dict_file is None:
        dict_file = "../../data/phrase_lists/republic-term-dictionary.json"
    with open(dict_file, 'rt') as fh:
        return json.load(fh)


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

doc_terms = [
    {'phrase': 'Missive', 'label': ['proposition:following', 'propositie_type:missive']},
    {'phrase': 'Brieff', 'label': ['proposition:following', 'propositie_type:brief']},
    {'phrase': 'Memoriael', 'label': ['proposition:following', 'propositie_type:memorie']},
    {'phrase': 'Remonstrantie', 'label': ['proposition:following', 'propositie_type:remonstrantie']},
    {'phrase': 'Requeste', 'label': ['proposition:following', 'propositie_type:rekest']},
    {'phrase': 'Concept', 'label': ['proposition:following', 'propositie_type:concept']},
    {'phrase': 'Rapport', 'label': ['proposition:following', 'propositie_type:rapport']},
    {'phrase': 'Memorie', 'label': ['proposition:following', 'propositie_type:memorie']},
    {'phrase': 'artijckel', 'label': ['proposition:following', 'propositie_type:artikel']}
]

proposition_opening_phrases = [
    {
        'phrase': 'ONtfangen een Missive van',
        'variants': [
            'ONtfangen twee Missiven van ',
            'Ontfangen een missive vanden '
        ],
        'label': [
            'proposition_opening',
            'proposition_from_correspondence',
            'propositie_type:missive'
        ],
        'proposition_type': 'missive',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'heeft ter Vergadering gecommuniceert ',
        'label': [
            'proposition_opening',
            'propositie_type:voordracht'
        ],
        'distractors': [
            'heeft ter Vergaderinge ingebraght',
            'heeft ter Vergaderinge voorgedragen',
        ],
        'proposition_type': 'voordracht',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': 'heeft aan haar Hoog Mog. voorgedragen',
        'label': [
            'proposition_opening',
            'propositie_type:voordracht'
        ],
        'variants': [
            'heeft ter Vergaderinge voorgedraagen',
            'heeft aan haar Hoog Mog. ingebraght',
            'heeft aan haar Hoog Mog. gecommuniceert',
        ],
        'proposition_type': 'voordracht',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': 'hebben ter Vergaderinge wederom voorgedraagen en vernieuwt, de Propositien',
        'label': [
            'proposition_opening',
            'propositie_type:voordracht'
        ],
        'proposition_type': 'voordracht',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': 'in gevolge en tot voldoeninge van der selver Resolutie commissoriaal van den',
        'label': [
            'reference',
            'reference_type:resolutie'
        ],
        'reference_type': 'resolutie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': ' hebben ter Vergaderinge wederom ',
        'label': [
            'proposition_opening',
            'propositie_type:onbekend'
        ],
        'proposition_type': 'onbekend',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': 'hebben ter Vergaderinge voorgedragen ',
        'label': [
            'proposition_opening',
            'propositie_type:voordracht'
        ],
        'variants': [
            'hebben ter Vergaderinge wederom voorgedragen ',
            'hebben ter Vergaderinge bekent gemaeckt'
        ],
        'distractors': [
            'heeft ter Vergaderinge ingebraght',
            'heeft ter Vergaderinge gecommuniceert',
        ],
        'proposition_type': 'voordracht',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': '  heeft ter Vergaderinge geëxhibeert een Pasport',
        'label': [
            'proposition_opening',
            'propositie_type:paspoort'
        ],
        'proposition_type': 'paspoort',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': ' heeft ter Vergadering geëxhibeert een Missive van',
        'label': [
            'proposition_opening',
            'propositie_type:missive'
        ],
        'proposition_type': 'missive',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': 'hebben ter Vergaderinge ingebragt en laaten leezen de Resolutie',
        'label': [
            'proposition_opening',
            'propositie_type:resolutie'
        ],
        'variants': [
            'heeft ter Vergaderinge ingebragt en laaten leezen de Resolutie ',
            'hebben ter Vergaderinge voorgedragen en laaten leesen der selver Resolutie'
        ],
        'proposition_type': 'resolutie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': 'hebben ter Vergaderinge ingebraght',
        'label': [
            'proposition_opening',
            'propositie_type:onbekend'
        ],
        'proposition_type': 'onbekend',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 500
    },
    {
        'phrase': 'IS ter Vergaderinge gelesen de Requeste van ',
        'label': [
            'proposition_opening',
            'propositie_type:rekest'
        ],
        'variants': [
            'IS ter Vergaderinge geëxhibeert een Resolutie van'
        ],
        'distractors': [
            'IS ter Vergaderinge gelesen de Memorie van ',
            'IS ter Vergaderinge gelesen het Advies van ',
            'IS ter Vergaderinge gelesen een Remonstrantie van',
        ],
        'proposition_type': 'requeste',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'IS ter Vergaderinge gelesen de Memorie van ',
        'label': [
            'proposition_opening',
            'propositie_type:memorie'
        ],
        'distractors': [
            'IS ter Vergaderinge gelesen de Requeste van ',
            'IS ter Vergaderinge gelesen het Advies van ',
            'IS ter Vergaderinge gelesen een Remonstrantie van'
        ],
        'proposition_type': 'memorie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'IS ter Vergaderinge gelesen het Advies van ',
        'label': [
            'proposition_opening',
            'propositie_type:advies'
        ],
        'distractors': [
            'IS ter Vergaderinge gelesen de Memorie van ',
            'IS ter Vergaderinge gelesen de Requeste van ',
            'IS ter Vergaderinge gelesen een Remonstrantie van'
        ],
        'proposition_type': 'advies',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'IS ter Vergaderinge gelesen het Remonstrantie van ',
        'label': [
            'proposition_opening',
            'propositie_type:remonstrantie'
        ],
        'distractors': [
            'IS ter Vergaderinge gelesen de Memorie van ',
            'IS ter Vergaderinge gelesen de Requeste van ',
            'IS ter Vergaderinge gelesen een Advies van'
        ],
        'proposition_type': 'remonstrantie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'IS gehoort het rapport van ',
        'variants': [
            'Is gehoort het rapport vande '
        ],
        'label': [
            'proposition_opening',
            'propositie_type:rapport'
        ],
        'proposition_type': 'rapport',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP de Requeste van ',
        'variants': [
            'Op de requeste van '
        ],
        'label': [
            'proposition_opening',
            'propositie_type:rekest'
        ],
        'proposition_type': 'requeste',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'ZYnde ter Vergaderinge getoont en geëxhibeert de Declaratie van ',
        'label': [
            'proposition_opening',
            'propositie_type:declaratie'
        ],
        'distractors': [
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Instructie van ',
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Reekening van ',
        ],
        'proposition_type': 'declaratie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'ZYnde ter Vergaderinge getoont en geëxhibeert de Instructie van ',
        'label': [
            'proposition_opening',
            'propositie_type:instructie'
        ],
        'distractors': [
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Declaratie van ',
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Reekening van ',
        ],
        'proposition_type': 'instructie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'ZYnde ter Vergaderinge getoont en geëxhibeert de Reekening van ',
        'label': [
            'proposition_opening',
            'propositie_type:rekening'
        ],
        'distractors': [
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Declaratie van ',
            'ZYnde ter Vergaderinge getoont en geëxhibeert de Instructie van ',
        ],
        'proposition_type': "rekening",
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'ZYnde ter Vergaderinge geëxhibeert vier Pasporten van',
        'label': [
            'proposition_opening',
            'propositie_type:paspoort'
        ],
        'proposition_type': 'paspoort',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP de Memorie van ',
        'label': [
            'proposition_opening',
            'propositie_type:memorie'
        ],
        'proposition_type': 'memorie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP het geproponeerde door den aenwesenden',
        'label': [
            'proposition_opening',
            'propositie_type:voordracht'
        ],
        'proposition_type': 'voordracht',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP het geproponeerde door',
        'label': [
            'proposition_opening',
            'propositie_type:onbekend'
        ],
        'proposition_type': 'onbekend',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP den differente gereezen voor de',
        'label': [
            'proposition_opening',
            'propositie_type:differente'
        ],
        'proposition_type': 'differente',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'BY resumptie gedelibereert zynde op de Missive ',
        'label': ['proposition_opening', 'propositie_type:missive'],
        'proposition_type': 'missive',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'BY resumptie gedelibereert zynde op de Requeste ',
        'label': ['proposition_opening', 'propositie_type:rekest'],
        'proposition_type': 'requeste',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'BY resumptie gedelibereert zynde op de rapport ',
        'label': ['proposition_opening', 'propositie_type:rapport'],
        'proposition_type': 'rapport',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'BY resumptie gedelibereert zynde op het geproponeerde ',
        'label': ['proposition_opening', 'propositie_type:voordracht'],
        'proposition_type': 'voordracht',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'BY Resumptie gedelibereert zynde',
        'label': ['proposition_opening', 'propositie_type:onbekend'],
        'proposition_type': 'onbekend',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'De requeste van ',
        'label': ['proposition_opening', 'propositie_type:rekest'],
        'proposition_type': 'requeste',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 2
    },
    {
        'phrase': 'DE Conclusie van versoek van',
        'label': ['proposition_opening', 'propositie_type:conclusie'],
        'proposition_type': 'conclusie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'DE Conclusie van Antwoord van',
        'label': ['proposition_opening', 'propositie_type:conclusie'],
        'proposition_type': 'conclusie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP de Conclusie van versoek om',
        'label': ['proposition_opening', 'propositie_type:conclusie'],
        'proposition_type': 'conclusie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'DE Conclusie van Duplicq van',
        'label': ['proposition_opening', 'propositie_type:conclusie'],
        'proposition_type': 'conclusie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP de Conclusie van Replicq op',
        'label': ['proposition_opening', 'propositie_type:conclusie'],
        'proposition_type': 'conclusie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'DE Conclusie van Eisch',
        'label': ['proposition_opening', 'propositie_type:conclusie'],
        'variants': [
            'DE Conclusie van eisen'
        ],
        'proposition_type': 'conclusie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'DE Conclusie van Eisch op de Requeste',
        'label': ['proposition_opening', 'propositie_type:conclusie'],
        'proposition_type': 'conclusie',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP het gerepresenteerde uit naam van sijn Hoogheid ter Vergaderinge gedaan',
        'label': ['proposition_opening', 'propositie_type:voordracht'],
        'proposition_type': 'voordracht',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP het gerepresenteerde ter Vergaderinge gedaan',
        'label': ['proposition_opening', 'propositie_type:voordracht'],
        'proposition_type': 'voordracht',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'OP het gerapporteerde van',
        'label': ['proposition_opening', 'propositie_type:rapport'],
        'proposition_type': 'rapport',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 10
    },
    {
        'phrase': 'DE Resolutien gisteren genomen',
        'variants': [
            'DE Resolutien eergisteren genomen',
            'DE Resolutien voorleede ',
            'DE Resolutien gisteren ge-',
        ],
        'label': 'reviewed',
        'start_year': 1637, 'end_year': 1796,
        'max_start_offset': 4
    },
    {
        'phrase': 'De resolutien gisteren genomen',
        'variants': [
            'De resolutien eergisteren genomen',
            'De resolutien voorleden ',
            'De resolutien gisteren ge-',
        ],
        'label': 'reviewed',
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 4
    },
    {
        'phrase': 'Ontfangen een Brieff',
        'variants': [
            'Ontfangen eenen brieff',
            'Ontfangen eenen anderen brieff',
            'Is gearresteert eenen brieff',
            'Is gearresteert den brieff',
        ],
        'label': ['proposition:opening', 'propositie_type:brief'],
        'start_year': 1576, 'end_year': 1640,
        'max_start_offset': 5
    },
    {
        'phrase': 'Ontfangen een missive vanden',
        'variants': [
        ],
        'label': ['proposition:opening', 'propositie_type:missive'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Opde Requeste van',
        'variants': [
            'Opde Requeste vande',
            'Opte reqte van'
        ],
        'label': ['proposition:opening', 'propositie_type:rekest'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is ter Vergaderinge gelesen',
        'variants': [
            'Synde ter Vergaderinge gelesen',
            'Synde gelesen'
        ],
        'label': ['proposition:opening', 'propositie_type:afhankelijk'],
        'followed_by': doc_terms,
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is gelesen de requeste van',
        'variants': [
            'Synde gelesen de requeste van'
        ],
        'label': ['proposition:opening', 'propositie_type:rekest'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': "Synde gehoort t'rapport van",
        'variants': [
            "Is gehoort t'rapport van"
        ],
        'label': ['proposition:opening', 'propositie_type:rapport'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is geordonneert ',
        'variants': [
            'Is oick geordonneert '
        ],
        'label': ['proposition:opening', 'propositie_type:ordonnantie'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is geresolueert ',
        'variants': [
            'Is oick geresolueert '
        ],
        'label': ['proposition:opening', 'propositie_type:resolutie'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is geproponeert',
        'variants': [
            'Is oick geproponeert',
            'Synde geproponeert'
        ],
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is geandtwoordt',
        'variants': [
        ],
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is goetgevonden',
        'variants': [
            'Is oock goetgevonden',
            'Is voorts oock goetgevonden'
        ],
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Ontfangen een',
        'variants': [
            'Synde ontfangen een'
        ],
        'label': ['proposition:opening', 'propositie_type:afhankelijk'],
        'start_year': 1576, 'end_year': 1704,
        'followed_by': doc_terms,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is gelesen het Translaet',
        'label': ['proposition:opening', 'propositie_type:afhankelijk'],
        'start_year': 1576, 'end_year': 1704,
        'followed_by': doc_terms,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is gearresteert ',
        'label': ['proposition:opening', 'propositie_type:afhankelijk'],
        'start_year': 1576, 'end_year': 1704,
        'followed_by': [
            {'phrase': "d'Instructie", 'label': ['proposition:following', 'propositie_type:instructie']},
            {'phrase': "d'Acte", 'label': ['proposition:following', 'propositie_type:acte']},
            {'phrase': "de Resolutie", 'label': ['proposition:following', 'propositie_type:resolutie']},
            {'phrase': "den Eedt", 'label': ['proposition:following', 'propositie_type:voordracht']},
        ],
        'max_start_offset': 5
    },
    {
        'phrase': 'Is gelesen het Concept',
        'label': ['proposition:opening', 'propositie_type:concept'],
        'variants': [
            'Is gelesen seecker Concept'
        ],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Sijn ter Vergaderinge gecompareert',
        'label': ['proposition:opening', 'propositie_type:voordracht'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is gecompareert',
        'label': ['proposition:opening', 'propositie_type:voordracht'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 3
    },
    {
        'phrase': "Opt versouck vande",
        'variants': [
            'Het versouck van'
        ],
        'label': ['proposition:opening', 'propositie_type:rekest'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': "Op de memorie van",
        'variants': [
        ],
        'label': ['proposition:opening', 'propositie_type:memorie'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': "Synde gelesen ende geresumeert t'concept van",
        'variants': [
            "Synde gelesen t'concept van"
        ],
        'label': ['proposition:opening', 'propositie_type:concept'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': "Synde gelesen de begrootinge van",
        'variants': [
            "Is gelesen de begrootinge van"
        ],
        'label': ['proposition:opening', 'propositie_type:begroting'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': "opgesocht ende gelesen de retroacta gevallen",
        'variants': [
        ],
        'label': ['proposition:opening', 'propositie_type:retroacta'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 150
    },
    {
        'phrase': 'Synde gedelibereert',
        'variants': [
            'Geresumeert synde',
            'Synde byden'
        ],
        'label': ['proposition:opening', 'propositie_type:afhankelijk'],
        'followed_by': doc_terms,
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is gelesen',
        'label': ['proposition:opening', 'propositie_type:afhankelijk'],
        'followed_by': doc_terms,
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Noch gelesen een',
        'label': ['proposition:opening', 'propositie_type:afhankelijk'],
        'followed_by': doc_terms,
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Item eenen brieff',
        'variants': [
            'Item eenen anderen brieff',
            'Item noch eenen anderen brieff',
            'Item brieuen',
            'Item andere brieuen'
        ],
        'label': ['proposition:opening', 'propositie_type:brief'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 1
    },
    {
        'phrase': 'Alsoo',
        'variants': [],
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 1
    },
    {
        'phrase': 'Item dat',
        'variants': [],
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 1
    },
    {
        'phrase': 'Is geaccordeert ',
        'variants': [],
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 1
    },
    {
        'phrase': 'Compareren',
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is den Griffier gelast te',
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Verclaert voorts',
        'label': ['proposition:opening', 'propositie_type:verklaring'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Gelesen de geconcipieerde Antwoirde',
        'label': ['proposition:opening', 'propositie_type:onbekend'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Is binnen gestaen ',
        'variants': [
            'Syn binnen gestaen '
        ],
        'label': ['proposition:opening', 'propositie_type:voordracht'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Die van Gelderlant Verclaren',
        'variants': [
            'Die van Hollant Verclaren',
            'Die van Vlaenderen Verclaren',
            'Die van Utrecht Verclaren',
            'Die van Brabant Verclaren',
            'Die van Vrieslant Verclaren',
            'Die van Zeelant Verclaren',
        ],
        'label': ['proposition:opening', 'propositie_type:voordracht'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': 'Rapporteert',
        'label': ['proposition:opening', 'propositie_type:rapport'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 3
    },
    {
        'phrase': 'Die heeren Gedepden. vande Provincien rapporteren',
        'variants': [
            'Die voors: Heeren Gedeputeerden vande Provincien rapporteren'
        ],
        'label': ['proposition:opening', 'propositie_type:rapport'],
        'start_year': 1576, 'end_year': 1630,
        'max_start_offset': 5
    },
    {
        'phrase': "D'heere",
        'variants': [
            'DHeer',
            'Den Agent'
        ],
        'label': ['proposition:opening', 'propositie_type:afhankelijk'],
        'start_year': 1576, 'end_year': 1630,
        'followed_by': [
            {'phrase': 'verclaert dat', 'label': ['proposition:following', 'propositie_type:voordracht']},
            {'phrase': 'rapporteert dat', 'label': ['proposition:following', 'propositie_type:rapport']},
            {'phrase': 'versouckt dat', 'label': ['proposition:following', 'propositie_type:voordracht']},
            {'phrase': 'communiceert dat', 'label': ['proposition:following', 'propositie_type:voordracht']},
            {'phrase': 'proponeert dat', 'label': ['proposition:following', 'propositie_type:voordracht']},
        ],
        'max_start_offset': 5
    },
    {
        'phrase': 'La lre de',
        'variants': [
            'Sur la lre',
            'Sur les lres',
            'Les lres de',
            'Accorde lre ',
            'Envoye lres ',
            'Receu lre ',
            'Receu lres',
            'Resolu de respondre aux lres de',
            'Sont arrestees les lres ',
            'Touchant les lres',
            'Touchant la lre'
        ],
        'label': [
            'proposition:opening', 'propositie_type:brief', 'lang:frans'
        ],
        'start_year': 1576, 'end_year': 1581,
        'max_start_offset': 3
    },
    {
        'phrase': 'Accorde de requerir ',
        'variants': [
            'On requiert de ',
            'Ordonne sur la Reqte des',
        ],
        'label': [
            'proposition:opening', 'propositie_type:rekest', 'lang:frans'
        ],
        'start_year': 1576, 'end_year': 1581,
        'max_start_offset': 3
    },
    {
        'phrase': 'Sur la Reqte.',
        'variants': [
            'Sur la Requeste',
            'Sur la reqte',
            'La Reqte. de',
            'La reqte de',
            'La reqte. de',
            'La reqte. des',
            'La reqte. van',
            'Quand a la Reqte.',
            'Touchant la reqte. de ',
            'Messieurs ont sur la reqte.',
            'Messieurs a la reqte. des',
            'Messieurs ont appoincte sur la reqte. de',

        ],
        'label': [
            'proposition:opening', 'propositie_type:rekest', 'lang:frans'
        ],
        'start_year': 1576, 'end_year': 1581,
        'max_start_offset': 3
    },
    {
        'phrase': 'Sur la Remonstrance',
        'variants': [
            'La Remonstrance de',
            'Quant a la Remonstrance'
        ],
        'label': [
            'proposition:opening', 'propositie_type:remonstrantie', 'lang:frans'
        ],
        'start_year': 1576, 'end_year': 1581,
        'max_start_offset': 3
    },
    {
        'phrase': 'Ordonne a',
        'variants': [
            'Les Estatz Generaulx ordonnent',
            'Les Estatz ont ordonne'
        ],
        'label': [
            'proposition:opening', 'propositie_type:ordonnantie', 'lang:frans'
        ],
        'start_year': 1576, 'end_year': 1581,
        'max_start_offset': 3
    },
    {
        'phrase': 'Sur la proposition',
        'variants': [
        ],
        'label': [
            'proposition:opening', 'propositie_type:voordracht', 'lang:frans'
        ],
        'start_year': 1576, 'end_year': 1581,
        'max_start_offset': 3
    },
    {
        'phrase': 'Resolu que',
        'variants': [
            'Resolu de',
            'Resolu d‛escrire',
            'Resolu d‛envoyer',
            'Resolu d‛escripre',
            'Resolu par',
            'Resolu sur',
            "Resolu d'accorder",
            'Resolu descripre',
            'Resolution sur',
            'Resolu descrire',
            'Resolution des',
            'Resolu pour',
            "Resolu d'accepter",
        ],
        'label': [
            'proposition:opening', 'propositie_type:resolution', 'lang:frans'
        ],
        'start_year': 1576, 'end_year': 1581,
        'max_start_offset': 3
    },
    {
        'phrase': 'Sur le memoire',
        'variants': [
            'Quant a la memoire',
        ],
        'label': [
            'proposition:opening', 'propositie_type:memorie', 'lang:frans'
        ],
        'start_year': 1576, 'end_year': 1581,
        'max_start_offset': 3
    },
    {
        'phrase': 'Pntes die voors',
        'label': 'attendance:repeat',
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Preside de heer',
        'label': ['attendance:start', 'attendance:president'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'Praeside en Praesentibus de Heeren',
        'label': ['attendance:start', 'attendance:repeat'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'als in het ordinaris Register',
        'label': ['attendance:start', 'attendance:repeat'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    },
    {
        'phrase': 'present de heeren',
        'label': ['attendance:start', 'attendance:deputies'],
        'start_year': 1576, 'end_year': 1704,
        'max_start_offset': 5
    }
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
        'phrase': "hebbende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "raeckende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "reclameerende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
    },
    {
        'phrase': "presenteerende",
        'label': ['proposition_verb', 'proposition_opening_end_verb', 'proposition_body'],
        'distractors': [
            'presideerende'
        ]
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
        'phrase': 'aanneemende',
        'label': ['proposition_verb', 'claim', 'proposition_body'],
        'distractors': [
            'waarneemende'
        ]
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
        'label': ['no_decision', 'resolution_decision'],
        'variants': [
            "Waer op geen resolutie is gevallen",
            "WAAR op geen resolutie voor alsnoch is gevallen",
            "Waer op geen resolutie voor alsnoch is gevallen",
        ],
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
        'phrase': 'haar Hoog Mogende',
        'label': ['title', 'organisation_title'],
        'variants': [
            'haar Hoog Mog.',
            'haar Ho. Mo.'
        ]
    },
    {
        'phrase': 'De Heeren Gedeputeerden van de Provincie',
        'label': ['organisation', 'states', 'province'],
    },
    {
        'phrase': 'de Heeren Staaten van de Provincie',
        'label': ['organisation', 'states', 'province'],
    },
    {
        'phrase': 'Staaten van de Provincie',
        'label': ['organisation', 'province', 'states'],
    },
    {
        'phrase': 'den Raad van Staate',
        'label': ['organisation', 'council_of_states'],
    },
    {
        'phrase': 'Raad der Stad',
        'label': ['organisation', 'city_council'],
    },
    {
        'phrase': 'den Eerste Raad',
        'label': ['organisation', 'council'],
    },
    {
        'phrase': 'den Eerst-presideerende Raad',
        'label': ['organisation', 'council'],
    },
    {
        'phrase': 'en andere Raaden',
        'label': ['organisation', 'council'],
    },
    {
        'phrase': 'de Generaliteits Reekenkamer',
        'label': ['organisation', 'proposer_title'],
    },
    {
        'phrase': 'by den Ryksdag',
        'label': ['organisation', 'german', 'political']
    },
    {
        'phrase': 'by het Department van',
        'label': ['organisation_relation', 'person_role'],
    },
    {
        'phrase': 'de Booden en Posten van',
        'label': ['organisation_relation', 'person_role'],
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
    {
        'phrase': 'aan het Hof van ',
        'label': ['representation_relation', 'organisation_relation']
    },
    {
        'phrase': 'van den Hove',
        'label': ['organisation']
    },
]

location_phrases = [
    {
        'phrase': 'Weftvriesland en den Noorder Quartiere',
        'label': 'location'
    },
    {
        'phrase': 'het Binnenhof ',
        'label': ['location']
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
        'phrase': 'het Overquartier van',
        'label': ['location_type', 'location_relation']
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
        'label': ['location_relation'],
        'distractors': [
            'den Handel in'
        ]
    },
    {
        'phrase': 'den Colonie van ',
        'label': ['location_relation']
    },
    {
        'phrase': 'de Kamers Griffie',
        'label': ['location', 'office', 'registrars_office'],
    },
    {
        'phrase': 'de Oostentycksche Nederlanden',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Groot Britannien',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Vranckrijk',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Pruissen',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Londen',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Parys',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Brussel',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Weenen',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Franckfort',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Regensburgh',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Berlyn',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Hamburg',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Stockholm',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Lissabon',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Keulen',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Madrid',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'St. Petersburg',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Koppenhagen',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Rotterdam',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Mentz',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Amsterdam',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Dresden',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Middelburg',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Venlo',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Groningen',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Dantzig',
        'label': ['location', 'region'],
    },
    {
        'phrase': "'s Hertogenbosch",
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Livorno',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Turin',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Utrecht',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Munster',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Maastricht',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Manheim',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Arnhem',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Algiers',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Barcelona',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Enckhuisen',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Goedesberg by Bonn',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Harlingen',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Leyden',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Maltha',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Paramaribo',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Waalwyk',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Eyndhoven',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Dordrecht',
        'label': ['location', 'region'],
    },
    {
        'phrase': 'Stad en Lande',
        'label': ['location', 'region'],
    },

]

esteem_titles = [

]


person_role_phrases = [
    {
        'phrase': 'Hooghschout ',
        'label': ['person_role', 'representative']
    },
    {
        'phrase': 'Quartierschout ',
        'label': ['person_role', 'representative']
    },
    {
        'phrase': 'Burger',
        'label': ['citizen', 'person_role']
    },
    {
        'phrase': 'den Resident',
        'label': ['citizen', 'person_role']
    },
    {
        'phrase': 'Huisvrouw',
        'label': ['citizen', 'person_role']
    },
    {
        'phrase': 'Weduwe',
        'label': ['citizen', 'person_role']
    },
    {
        'phrase': 'Weduwnaar',
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
        'phrase': 'de gesaamenlijke Leydeckers Knegts van',
        'label': ['person_role', 'laborer', 'representation_relation']
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
        'phrase': 'Lieutenant',
        'label': ['person_role', 'lieutenant', 'domain:military'],
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
        'variants': [
            'Advocaat voor'
        ]
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
        'phrase': 'Contrarolleur van',
        'label': ['person_role', 'controller'],
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
        'phrase': 'Balliuw',
        'label': ['person_role', 'representative', 'magistrate'],
        'role': 'magistrate_single'
    },
    {
        'phrase': 'Burgemeester',
        'label': ['person_role', 'representative', 'magistrate'],
        'role': 'magistrate_single'
    },
    {
        'phrase': 'Scheepenen',
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
        'phrase': 'Schipper',
        'label': ['person_role', 'merchant'],
    },
    {
        'phrase': 'Leverancier',
        'label': ['person_role', 'merchant'],
    },
    {
        'phrase': 'Drossard',
        'label': ['person_role', 'merchant'],
    },
    {
        'phrase': 'Regent',
        'label': ['person_role', 'merchant'],
        'variants': ['Regenten']
    },
    {
        'phrase': 'Boekhouder',
        'label': ['person_role', 'merchant'],
    },
    {
        'phrase': 'Koopman',
        'label': ['person_role', 'merchant'],
        'variants': [
            'Koopvrouw'
        ]
    },
    {
        'phrase': 'Kooplieden',
        'label': ['person_role', 'merchant', 'merchant_multi'],
        'variants': [
            'Koopluyden'
        ]
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

proposition_from_phrases = [
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
            'wordende met',
            'houdende te',
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
        'phrase': 'alhier te den Hage',
        'label': ['active_in_location', 'person_location', 'location:the_hague'],
        'variants': [
        ],
    },
    {
        'phrase': 'den 1 deeser loopende maand',
        'label': ['current_month', 'temporal_reference'],
        'variants': [
            'den 1 en 2 deeser loopende maand',
            'den tienden deeser loopende maand',
            'den elfden deeser loopende maand',
            'den twaalfden deeser loopende maand',
            'den dertienden deeser loopende maand',
            'den zestienden deeser loopende maand',
            'den negentienden deeser loopende maand',
            'den seeven en twintighsten deeser loopende maand',
        ]
    },
    {
        'phrase': 'den .. der voorleeden maand',
        'label': ['previous_month', 'temporal_reference'],
        'variants': [
            'den 1 en 2 der voorleeden maand',
            'den tienden der voorleeden maand',
            'den elfden der voorleeden maand',
            'den twaalfden der voorleeden maand',
            'den dertienden der voorleeden maand',
            'den zestienden der voorleeden maand',
            'den negentienden der voorleeden maand',
            'den seeven en twintighsten der voorleeden maand',
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
        'phrase': 'geaddresseert aan ',
        'label': 'addressed_to'
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
    {
        'phrase': 'den Handel in',
        'label': ['trade', 'trade_relation'],
        'distractors': [
            'den Lande van'
        ]
    },
    {
        'phrase': 'de Vaart en Handel op de West-indien',
        'label': ['topic', 'topic:trade', 'domain:maritime'],
        'variants': [
            'den Westindische Handel'
        ]
    },
    {
        'phrase': 'tot de saaken van',
        'label': ['topic_prefix', 'affairs_relation']
    },
    {
        'phrase': 'tot de saaken van de Finantie',
        'label': ['topic', 'topic:finance', 'affairs_relation']
    },
    {
        'phrase': 'tot de buitenlandse saaken',
        'label': ['topic', 'topic:foreign_affairs', 'domain:politics', 'department', 'affairs_relation']
    },
]

provinces = [
    {
        'phrase': ' van Holland en Westvriesland',
        'label': 'of_province',
        'variants': [
            'van Hollandt ende West - Vrieslandt'
        ]
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


known_persons = [
    {
        'phrase': 'Fagel',
        'label': ['person_name', 'griffier_name']
    }
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

resolution_phrase_sets = {
    'proposition_opening_phrases': proposition_opening_phrases,
    'proposition_reason_phrases': proposition_reason_phrases,
    'proposition_closing_phrases': proposition_closing_phrases,
    'proposition_from_phrases': proposition_from_phrases,
    'proposition_verbs': proposition_verbs,
    'decision_phrases': decision_phrases,
    'resolution_link_phrases': resolution_link_phrases,
    'prefix_phrases': prefix_phrases,
    'organisation_phrases': organisation_phrases,
    'location_phrases': location_phrases,
    'esteem_titles': esteem_titles,
    'person_role_phrases': person_role_phrases,
    'military_phrases': military_phrases,
    'misc': misc,
    'provinces': provinces
}

