import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add backend directory to sys.path to support execution from repository root
sys.path.append(str(Path(__file__).resolve().parent))

import database


class SupabaseDatabaseTests(unittest.TestCase):
    @patch.object(database.db, "request", side_effect=[[{"id": 1}], [{"id": 2}]])
    def test_duplicate_filenames_are_allowed_for_multiple_documents(self, request):
        first_id = database.add_document("alpha_policy.txt", "1 KB", status="Indexed", company="TCS")
        second_id = database.add_document("alpha_policy.txt", "2 KB", status="Indexed", company="Infosys")

        self.assertEqual((first_id, second_id), (1, 2))
        self.assertEqual(request.call_count, 2)
        first_payload = request.call_args_list[0].kwargs["json"]
        second_payload = request.call_args_list[1].kwargs["json"]
        self.assertEqual(first_payload["filename"], second_payload["filename"])
        self.assertNotEqual(first_payload["company"], second_payload["company"])


if __name__ == "__main__":
    unittest.main()
