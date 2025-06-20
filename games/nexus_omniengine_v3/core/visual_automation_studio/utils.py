"""
Visual Automation Studio Utilities: Nexus OmniEngine v3.0
Drake v0.3 protocol, TPC-compliant
Utility functions for workflow and automation modules.
"""

import os
import json


def load_workflow(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_workflow(workflow: dict, path: str):
    with open(path, "w") as f:
        json.dump(workflow, f, indent=2)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
