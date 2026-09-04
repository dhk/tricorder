import unittest

from tricorder.llm.providers import MIN_HARD_TIMEOUT_S, call_budget_s


class CallBudgetTest(unittest.TestCase):
    def test_ordinary_calls_get_the_floor(self):
        self.assertEqual(call_budget_s(1024), MIN_HARD_TIMEOUT_S)
        self.assertEqual(call_budget_s(2048), MIN_HARD_TIMEOUT_S)

    def test_large_responses_get_more_time(self):
        self.assertEqual(call_budget_s(4096), 132)
        self.assertEqual(call_budget_s(8192), 234)
        self.assertGreater(call_budget_s(8192), call_budget_s(4096))


if __name__ == "__main__":
    unittest.main()
