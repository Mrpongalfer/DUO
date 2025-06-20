from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="nexus_omniengine_v3",
    version="0.1.0",
    description="Nexus OmniEngine v3.0: AI/Ansible Hybrid Automation Platform",
    author="Omnitide Nexus Architect",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": ["nexus-omni-tui=core.universal_tui.tui_app:main"]
    },
    package_data={
        "": [
            "config/*.json",
            "docs/*.md",
            "nexus_ansible/**/*.yml",
            "gui/templates/*.html",
            "instruction_schema.json",
            "orchestrator_state.json",
        ]
    },
    python_requires=">=3.10",
)
