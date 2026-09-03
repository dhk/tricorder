import unittest

from tricorder.lenses import load_lens
from tricorder.lenses.prompting import coerce_categories


class CoerceCategoriesTest(unittest.TestCase):
    def test_unknown_values_become_other_and_are_recorded(self):
        lens = load_lens("product-engineering-desktop")
        result = {"patterns": [
            {"category": "ipc-boundary"},
            {"category": "build-release-scripts"},     # a file tag, not a category
            {"category": "Error Handling"},            # normalisable
            {"category": None},
        ]}
        n = coerce_categories(result, lens)
        cats = [p["category"] for p in result["patterns"]]
        self.assertEqual(cats, ["ipc-boundary", "other", "error-handling", "other"])
        self.assertEqual(n, 2)
        self.assertEqual(result["_coerced_categories"], 2)
        self.assertEqual(result["patterns"][1]["_category_raw"], "build-release-scripts")
        self.assertNotIn("_category_raw", result["patterns"][2])

    def test_clean_result_is_untouched(self):
        lens = load_lens("analytics-engineering")
        result = {"patterns": [{"category": "grain"}, {"category": "testing"}]}
        self.assertEqual(coerce_categories(result, lens), 0)
        self.assertNotIn("_coerced_categories", result)


if __name__ == "__main__":
    unittest.main()
