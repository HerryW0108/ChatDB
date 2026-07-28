import os
import unittest
from unittest.mock import patch

import SQL


class SqlTests(unittest.TestCase):
    def test_detect_query_type_from_natural_language(self):
        cases = {
            "Please select two columns": "select",
            "I want a GROUP BY query": "group by",
            "Can you join these tables?": "join",
            "Filter it with a where clause": "where",
            "Show me something useful": None,
        }

        for user_input, expected in cases.items():
            with self.subTest(user_input=user_input):
                self.assertEqual(SQL.detect_query_type(user_input), expected)

    def test_generated_query_quotes_reserved_mysql_identifier(self):
        table_info = {"constructorResults": ["group"]}

        self.assertEqual(
            SQL.generate_select_query(table_info),
            "SELECT `group` FROM `constructorResults`;",
        )

        with patch(
            "SQL.random.choice",
            side_effect=["constructorResults", "group", "group", "COUNT"],
        ):
            group_by_query = SQL.generate_group_by_query(table_info)

        self.assertEqual(
            group_by_query,
            "SELECT `group`, COUNT(`group`) "
            "FROM `constructorResults` GROUP BY `group`;",
        )

    def test_mysql_connection_uses_environment(self):
        values = {
            "MYSQL_HOST": "db.example.test",
            "MYSQL_PORT": "3307",
            "MYSQL_USER": "chatdb",
            "MYSQL_PASSWORD": "test-password",
        }

        with (
            patch.dict(os.environ, values, clear=False),
            patch("SQL.mysql.connector.connect") as connect,
        ):
            connection = SQL.connect_to_sql_database()

        self.assertIs(connection, connect.return_value)
        connect.assert_called_once_with(
            host="db.example.test",
            port=3307,
            user="chatdb",
            password="test-password",
        )


if __name__ == "__main__":
    unittest.main()
