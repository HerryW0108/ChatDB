import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

import MongoDB_Final
import Mongo_execution


class MongoExecutionTests(unittest.TestCase):
    def test_parse_find_without_projection(self):
        collection, query_filter, projection = Mongo_execution.parse_find_query(
            "db.usercuisine.find({'Rcuisine': {'$eq': 'American'}})"
        )

        self.assertEqual(collection, "usercuisine")
        self.assertEqual(query_filter, {"Rcuisine": {"$eq": "American"}})
        self.assertIsNone(projection)

    def test_parse_find_with_projection(self):
        collection, query_filter, projection = Mongo_execution.parse_find_query(
            "db.usercuisine.find("
            "{'Rcuisine': {'$eq': 'American'}}, "
            "{'userID': 1, '_id': 0})"
        )

        self.assertEqual(collection, "usercuisine")
        self.assertEqual(query_filter, {"Rcuisine": {"$eq": "American"}})
        self.assertEqual(projection, {"userID": 1, "_id": 0})

    def test_parse_find_rejects_non_find_expression(self):
        with self.assertRaises(ValueError):
            Mongo_execution.parse_find_query("db.usercuisine.delete_many({})")

    def test_execute_find_passes_structured_arguments_to_pymongo(self):
        collection = MagicMock()
        fake_db = MagicMock()
        fake_db.__getitem__.return_value = collection

        with patch.object(Mongo_execution, "db", fake_db):
            Mongo_execution.execute_find(
                "db.usercuisine.find({'Rcuisine': 'American'}, {'userID': 1})"
            )

        collection.find.assert_called_once_with(
            {"Rcuisine": "American"}, {"userID": 1}
        )


class MongoWorkflowTests(unittest.TestCase):
    def test_bundled_datasets_load_outside_project_directory(self):
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            try:
                os.chdir(temporary_directory)
                datasets = MongoDB_Final.load_datasets()
            finally:
                os.chdir(original_directory)

        self.assertEqual(
            set(datasets), {"usercuisine", "userpayment", "userprofile"}
        )
        self.assertEqual(len(datasets["userprofile"]), 138)

    def test_find_in_operator_coerces_numeric_values(self):
        data = pd.DataFrame({"birth_year": [1989, 1990]})

        with patch(
            "builtins.input",
            side_effect=["birth_year", "in", "1989, 1990", "no", ""],
        ):
            query = MongoDB_Final.generate_find_query(data, "userprofile")

        self.assertEqual(
            query["filter"],
            {"birth_year": {"$in": [1989, 1990]}},
        )

    def test_aggregate_retries_invalid_operator_and_builds_numeric_in_list(self):
        data = pd.DataFrame({"birth_year": [1989, 1990]})
        datasets = {"userprofile": data}

        with patch(
            "builtins.input",
            side_effect=[
                "yes",
                "birth_year",
                "approximately",
                "in",
                "1989, 1990",
                "no",
                "no",
                "no",
                "no",
                "no",
                "birth_year",
            ],
        ):
            pipeline = MongoDB_Final.generate_aggregate_query(
                data,
                "userprofile",
                datasets,
            )

        self.assertEqual(
            pipeline,
            [
                {"$match": {"birth_year": {"$in": [1989, 1990]}}},
                {
                    "$project": {
                        "birth_year": "$birth_year",
                        "_id": 0,
                    }
                },
            ],
        )

    def test_example_aggregate_executes_through_bound_module(self):
        datasets = {"usercuisine": pd.DataFrame({"userID": ["U1001"]})}
        example_query = (
            "db.usercuisine.aggregate(["
            "{'$group': {'_id': '$userID', 'count': {'$sum': 1}}}"
            "])"
        )

        with (
            patch("builtins.input", side_effect=["example", "2", "yes", "quit"]),
            patch.object(MongoDB_Final, "load_datasets", return_value=datasets),
            patch.object(
                MongoDB_Final,
                "generate_example_queries",
                return_value=[{"query": example_query}],
            ),
            patch.object(
                MongoDB_Final,
                "display_example_queries",
                return_value=example_query,
            ),
            patch.object(
                MongoDB_Final.execution, "execute_aggregate"
            ) as execute_aggregate,
        ):
            MongoDB_Final.chat_with_user()

        execute_aggregate.assert_called_once_with(
            "usercuisine",
            [{"$group": {"_id": "$userID", "count": {"$sum": 1}}}],
        )


if __name__ == "__main__":
    unittest.main()
