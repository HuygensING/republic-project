import datetime
from unittest import TestCase

import republic.model.republic_date as republic_date


class TestDateNameMapInit(TestCase):

    def setUp(self) -> None:
        self.text_type = 'handwritten'
        self.res_type = 'ordinaris'
        self.period_start = 1600
        self.period_end = 1700
        self.date_name_map = republic_date.default_date_name_map[0]
        self.date_mapper = republic_date.DateNameMapper(text_type=self.text_type,
                                                        resolution_type=self.res_type,
                                                        period_start=self.period_start,
                                                        period_end=self.period_end)

    def test_date_name_map_uses_default(self):
        date_mapper = republic_date.DateNameMapper(text_type=self.text_type,
                                                   resolution_type=self.res_type,
                                                   period_start=self.period_start,
                                                   period_end=self.period_end)
        self.assertEqual(self.text_type, date_mapper.date_name_map['text_type'])

    def test_date_name_map_can_set_text_type(self):
        text_type = 'printed'
        period_start = 1705
        period_end = 1796
        date_mapper = republic_date.DateNameMapper(text_type=text_type,
                                                   resolution_type=self.res_type,
                                                   period_start=period_start,
                                                   period_end=period_end)
        self.assertEqual(text_type, date_mapper.text_type)

    def test_date_name_map_can_set_resolution_type(self):
        resolution_type = 'secreet'
        date_mapper = republic_date.DateNameMapper(text_type=self.text_type,
                                                   resolution_type=resolution_type,
                                                   period_start=self.period_start,
                                                   period_end=self.period_end)
        self.assertEqual(resolution_type, date_mapper.resolution_type)

    def test_date_name_map_checks_valid_text_type(self):
        text_type = 'spoken'
        self.assertRaises(ValueError, republic_date.DateNameMapper,
                          text_type=text_type, resolution_type=self.res_type,
                          period_start=self.period_start,
                          period_end=self.period_end)

    def test_date_name_map_checks_valid_resolution_type(self):
        res_type = 'public'
        self.assertRaises(ValueError, republic_date.DateNameMapper,
                          text_type=self.text_type, resolution_type=res_type,
                          period_start=self.period_start,
                          period_end=self.period_end)

    def test_date_name_map_checks_period_is_in_map(self):
        period_start, period_end = 1200, 1300
        self.assertRaises(ValueError, republic_date.DateNameMapper,
                          text_type=self.text_type, resolution_type=self.res_type,
                          period_start=period_start,
                          period_end=period_end)


class TestDateNameMapperSetMap(TestCase):

    def setUp(self) -> None:
        self.text_type = 'handwritten'
        self.res_type = 'ordinaris'
        self.period_start = 1600
        self.period_end = 1700
        self.date_name_map = republic_date.default_date_name_map[0]
        self.date_mapper = republic_date.DateNameMapper(text_type=self.text_type,
                                                        resolution_type=self.res_type,
                                                        period_start=self.period_start,
                                                        period_end=self.period_end)

    def test_mapper_sets_week_day_names(self):
        self.assertEqual(True, 'Martis' in self.date_mapper.index_week_day[1])

    def test_mapper_sets_multiple_week_day_names_per_index(self):
        self.assertEqual(True, len(self.date_mapper.index_week_day) > 1)

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
        self.assertEqual(True, any(['Laesten' in day_string for day_string in day_strings]))

    def test_mapper_can_generate_correct_last_but_one_day_of_the_month(self):
        year, month, day = 1612, 4, 29
        include_year = True
        day_strings = self.date_mapper.generate_day_string(year, month, day,
                                                           include_year=include_year)
        self.assertEqual(True, any(['naestlesten' in day_string for day_string in day_strings]))
