#!/usr/bin/python
# -*- encoding: utf8 -*-
import unittest

from back_office.test_back_office import TestBackOffice
from mis_translator.test_mis_api_stub import TestStub
from mis_translator.test_mis_api_navitia import TestNavitia, TestNavitiaMisApi
from planner.test_plan_trip_calculator import TestPlanTripCalculator
from planner.test_planner import TestPlanner

if __name__ == '__main__':
    unittest.main()
