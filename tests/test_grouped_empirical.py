import unittest

from realitygraph.grouped_empirical import (
    _occupancy_rows,
    _parkinsons_rows,
)


class GroupedEmpiricalTests(unittest.TestCase):
    def test_parkinsons_recordings_collapse_to_subject_group(self):
        raw = (
            "name,f1,status,f2\n"
            "phon_R01_S01_1,1.0,1,2.0\n"
            "phon_R01_S01_2,1.5,1,2.5\n"
            "phon_R01_S02_1,3.0,0,4.0\n"
        ).encode()
        rows = list(_parkinsons_rows(raw))
        self.assertEqual(rows[0][0], ("f1", "f2"))
        self.assertEqual(rows[0][3], "phon_R01_S01")
        self.assertEqual(rows[1][3], "phon_R01_S01")
        self.assertEqual(rows[2][3], "phon_R01_S02")
        self.assertEqual(rows[0][2], 1)
        self.assertEqual(rows[2][2], 0)

    def test_occupancy_rows_group_by_calendar_day(self):
        raw = (
            '"","date","Temperature","Humidity","Light","CO2","HumidityRatio","Occupancy"\n'
            '"1","2015-02-04 17:51:00",23.18,27.27,426,721.25,0.00479,1\n'
            '"2","2015-02-04 17:52:00",23.15,27.26,429,714.00,0.00478,1\n'
            '"3","2015-02-05 08:00:00",20.00,30.00,0,500.00,0.00400,0\n'
        ).encode()
        rows = list(_occupancy_rows(raw))
        self.assertEqual(rows[0][2], "2015-02-04")
        self.assertEqual(rows[1][2], "2015-02-04")
        self.assertEqual(rows[2][2], "2015-02-05")
        self.assertEqual(rows[0][1], 1)
        self.assertEqual(rows[2][1], 0)
        self.assertEqual(len(rows[0][0]), 5)


if __name__ == "__main__":
    unittest.main()
