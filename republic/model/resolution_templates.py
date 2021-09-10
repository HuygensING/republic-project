
opening_templates = [
    {
        "label": "proposition_from_correspondence",
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
                    {"label": "person_name_prefix", "required": False, "cardinality": "multi"},
                    {"label": "title", "required": False, "cardinality": "multi"},
                    {"label": "proposer_name", "required": False, "variable": True},
                    {"label": "person_role", "required": False, "cardinality": "multi"},
                    {"label": "representation_relation", "required": False},
                    {"label": "affairs_relation", "required": False},
                    {"label": "resolution_relation", "required": False},
                    {"label": "location_relation", "required": False},
                    {"label": "location", "required": False, "variable": True},
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
                    {"label": "person_location", "required": False},
                    {"label": "location_relation", "required": False},
                    {"label": "location", "required": False, "variable": True},
                    {"label": "temporal_reference", "required": False},
                    {"label": "addressed_to", "required": False},
                    {"label": "person_name_prefix", "required": False, "cardinality": "multi"},
                    {"label": "person_role", "required": False, "cardinality": "multi"},
                    {"label": "addressee_name", "required": False, "variable": True},
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
    },
    {
        'label': 'proposition_from_statement',
        'ordered': True,
        'type': 'group',
        'elements': [
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
                    {"label": "person_name_prefix", "required": False, "cardinality": "multi"},
                    {"label": "title", "required": False, "cardinality": "multi"},
                    {"label": "proposer_name", "required": False, "variable": True},
                    {"label": "person_role", "required": False, "cardinality": "multi"},
                    {"label": "representation_relation", "required": False},
                    {"label": "affairs_relation", "required": False},
                    {"label": "resolution_relation", "required": False},
                    {"label": "location_relation", "required": False},
                    {"label": "location", "required": False, "variable": True},
                    {"label": "organisation", "required": False},
                ]
            },
            {
                "label": "proposition_origin",
                "type": "group",
                "ordered": True,
                "elements": [
                    {"label": "resident_in", "required": False},
                    {"label": "residence_relation", "required": False},
                    {"label": "location", "required": False, "variable": True},
                    {"label": "temporal_reference", "required": False},
                    {"label": "addressed_to", "required": False},
                    {"label": "person_name_prefix", "required": False, "cardinality": "multi"},
                    {"label": "person_role", "required": False, "cardinality": "multi"},
                    {"label": "addressee_name", "required": False, "variable": True},
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
    },
    {
        'label': 'proposition_short_request',
        'ordered': True,
        'type': 'group',
        'elements': [
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
                    {"label": "person_name_prefix", "required": False, "cardinality": "multi"},
                    {"label": "title", "required": False, "cardinality": "multi"},
                    {"label": "proposer_name", "required": False, "variable": True},
                    {"label": "person_role", "required": False, "cardinality": "multi"},
                    {"label": "representation_relation", "required": False},
                    {"label": "affairs_relation", "required": False},
                    {"label": "resolution_relation", "required": False},
                    {"label": "location_relation", "required": False},
                    {"label": "location", "required": False, "variable": True},
                    {"label": "organisation", "required": False},
                ]
            },
            {
                "label": "proposition_origin",
                "type": "group",
                "ordered": True,
                "elements": [
                    {"label": "resident_in", "required": False},
                    {"label": "residence_relation", "required": False},
                    {"label": "location", "required": False, "variable": True},
                    {"label": "temporal_reference", "required": False},
                    {"label": "addressed_to", "required": False},
                    {"label": "person_name_prefix", "required": False, "cardinality": "multi"},
                    {"label": "person_role", "required": False, "cardinality": "multi"},
                    {"label": "addressee_name", "required": False, "variable": True},
                ]
            },
            {
                "label": "resolution_decision",
                "type": "group",
                "elements": [
                    {"label": "resolution_decision", "required": False},
                ]
            }
        ]
    },
]

template_sets = {
    'opening_templates': opening_templates
}
