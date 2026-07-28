import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

import MongoDB_Final
import SQL
import landing_page


PROJECT_DIR = Path(__file__).resolve().parents[1]

EXPECTED_CSV_HASHES = {
    "constructorResults.csv": (
        "4793b58d7ceb61eff3686199375cd63d8e5ae2f4494f2d1e4494fd7af64cdd59"
    ),
    "constructorStandings.csv": (
        "0ac47aa74a76d46b1dd14645df8d7603b26e8e784d6ec0073f67165b3ae8cacc"
    ),
    "qualifying.csv": (
        "411efc76cb758458e224054703c509e589d4dd529581c1da486a762817cfd586"
    ),
    "usercuisine.csv": (
        "2cb93a2c5432ccd0d2ece72e60ec0f79fd08339a78006ed8c945fd1100e90e80"
    ),
    "userpayment.csv": (
        "92b25576fd7582109e0ff12db60811cb8b4d1e01c102079c905ba9ffb138c696"
    ),
    "userprofile.csv": (
        "9ac765bf4731d7ce322580f33b472b4fa96409cc626390286affee097152bfb3"
    ),
}


class ApplicationTests(unittest.TestCase):
    def test_main_menu_dispatches_both_workflows_and_exits(self):
        with (
            patch("builtins.input", side_effect=["1", "2", "3"]),
            patch.object(SQL, "run_SQL") as run_sql,
            patch.object(MongoDB_Final, "chat_with_user") as run_mongo,
        ):
            landing_page.greet_user()

        run_sql.assert_called_once_with()
        run_mongo.assert_called_once_with()

    def test_bundled_csv_files_remain_byte_for_byte_unchanged(self):
        for filename, expected_hash in EXPECTED_CSV_HASHES.items():
            with self.subTest(filename=filename):
                digest = hashlib.sha256((PROJECT_DIR / filename).read_bytes()).hexdigest()
                self.assertEqual(digest, expected_hash)


if __name__ == "__main__":
    unittest.main()
