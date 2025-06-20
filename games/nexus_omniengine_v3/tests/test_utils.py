"""
Test: utils.py
Drake v0.3 protocol, TPC-compliant
"""

import unittest
import os
import tempfile
from games.nexus_omniengine_v3.core.visual_automation_studio.utils import load_workflow, save_workflow, ensure_dir


class TestUtils(unittest.TestCase):
    def test_ensure_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "a/b/c")
            ensure_dir(test_path)
            self.assertTrue(os.path.isdir(test_path))

    def test_load_and_save_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "workflow.json")
            data = {"foo": "bar"}
            save_workflow(data, path)
            loaded = load_workflow(path)
            self.assertEqual(data, loaded)


if __name__ == "__main__":
    unittest.main()
