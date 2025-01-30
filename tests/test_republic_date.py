import json
from unittest import TestCase

import republic.model.republic_date as republic_date
from republic.model.inventory_mapping import read_inventory_metadata


class TestMakeDateNameMap(TestCase):

    def setUp(self) -> None:
        self.date_line_elements = [
            ('weekday_name', 'handwritten'),
            ('den', 'all'),
            ('month_day_name', 'decimal_en'),
            ('month_name', 'handwritten'),
        ]

    def test_make_date_name_map_returns_dict(self):
        date_name_map = republic_date.make_date_name_map(self.date_line_elements)
        self.assertEqual(dict, type(date_name_map))

    def test_make_date_name_map_returns_dict_per_element(self):
        date_name_map = republic_date.make_date_name_map(self.date_line_elements)
        for ei, element in enumerate(date_name_map):
            with self.subTest(ei):
                if element in {'include_year', 'include_den'}:
                    self.assertEqual(bool, type(date_name_map[element]))
                else:
                    self.assertEqual(dict, type(date_name_map[element]))

    def test_make_date_name_map_can_include_year(self):
        date_line_elements = [(key, val) for key, val in self.date_line_elements]
        date_line_elements.append(('year', 'all'))
        date_name_map = republic_date.make_date_name_map(date_line_elements)
        self.assertEqual(True, date_name_map['include_year'])


class TestDateNameMapInit(TestCase):

    def setUp(self) -> None:
        invs_meta = read_inventory_metadata()
        self.inv_meta = {inv['inventory_num']: inv for inv in invs_meta}
        self.date_line_elements = [
            ('weekday_name', 'handwritten'),
            ('den', 'all'),
            ('month_day_name', 'decimal_en'),
            ('month_name', 'handwritten'),
        ]
        self.date_mapper = republic_date.DateNameMapper(inv_metadata=self.inv_meta[3168],
                                                        date_elements=self.date_line_elements)

    def test_date_name_map_uses_default(self):
        self.date_mapper = republic_date.DateNameMapper(inv_metadata=self.inv_meta[3168],
                                                        date_elements=self.date_line_elements)
        date_strings = self.date_mapper.generate_day_string(1608, 12, 8)
        self.assertIn('Lunae den 8en December', date_strings)

    def test_mapper_sets_weekday_names(self):
        self.assertEqual(True, 'Martis' in self.date_mapper.index_weekday[1])

    def test_mapper_sets_multiple_weekday_names_per_index(self):
        self.assertEqual(True, len(self.date_mapper.index_weekday) > 1)

    def test_mapper_sets_month_names(self):
        self.assertEqual(True, 'April' in self.date_mapper.index_month[4])

    def test_mapper_sets_multiple_month_names_per_index(self):
        self.assertEqual(True, len(self.date_mapper.index_month) > 1)

    def test_mapper_sets_month_day_name_when_available(self):
        self.assertEqual(True, len(self.date_mapper.index_month_day) > 1)

    def test_mapper_can_generate_day_string(self):
        year, month, day = 1612, 4, 19
        day_string = self.date_mapper.generate_day_string(year, month, day)
        self.assertEqual(True, day_string is not None)

    def test_mapper_can_generate_day_string_without_year(self):
        year, month, day = 1612, 4, 19
        include_year = False
        day_strings = self.date_mapper.generate_day_string(year, month, day,
                                                           include_year=include_year)
        self.assertEqual(True, all([str(year) not in day_string for day_string in day_strings]))


class TestDateNameMapYear(TestCase):

    def setUp(self) -> None:
        invs_meta = read_inventory_metadata()
        self.inv_meta = {inv['inventory_num']: inv for inv in invs_meta}
        self.date_line_elements = [
            ('weekday_name', 'handwritten'),
            ('den', 'all'),
            ('month_day_name', 'roman_en'),
            ('month_name', 'handwritten'),
            ('year', 'all')
        ]
        self.date_mapper = republic_date.DateNameMapper(inv_metadata=self.inv_meta[3168],
                                                        date_elements=self.date_line_elements)

    def test_mapper_can_generate_day_strings_with_year(self):
        year, month, day = 1612, 4, 19
        include_year = True
        day_strings = self.date_mapper.generate_day_string(year, month, day,
                                                           include_year=include_year)
        self.assertEqual(True, all([str(year) in day_string for day_string in day_strings]))

    def test_mapper_can_generate_correct_last_day_of_the_month(self):
        year, month, day = 1612, 4, 30
        include_year = True
        day_strings = self.date_mapper.generate_day_string(year, month, day,
                                                           include_year=include_year)
        print(day_strings)
        self.assertEqual(True, any(['Laesten' in day_string for day_string in day_strings]))

    def test_mapper_can_generate_correct_last_but_one_day_of_the_month(self):
        year, month, day = 1612, 4, 29
        include_year = True
        day_strings = self.date_mapper.generate_day_string(year, month, day,
                                                           include_year=include_year)
        self.assertEqual(True, any(['naestlesten' in day_string for day_string in day_strings]))
