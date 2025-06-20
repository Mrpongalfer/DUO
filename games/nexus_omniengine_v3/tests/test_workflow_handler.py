"""
Test: workflow_handler.py
Drake v0.3 protocol, TPC-compliant
"""

import unittest
from games.nexus_omniengine_v3.core.visual_automation_studio.workflow_handler import WorkflowHandler


class TestWorkflowHandler(unittest.TestCase):
    def test_validate(self):
        handler = WorkflowHandler({"name": "test", "steps": []})
        self.assertTrue(handler.validate())

    def test_invalid(self):
        handler = WorkflowHandler("not a dict")
        with self.assertRaises(ValueError):
            handler.validate()


if __name__ == "__main__":
    unittest.main()
