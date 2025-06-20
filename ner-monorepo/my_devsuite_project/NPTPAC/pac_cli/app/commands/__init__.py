# ner-monorepo/my_devsuite_project/NPTPAC/pac_cli/app/commands/__init__.py
# PAC CLI Commands

# This allows 'from app.commands import ner_cmds, lily_cmds' etc.
# You might have specific modules listed here or use __all__.
# For simplicity, ensuring main.py can find lily_cmds.py in the same 'commands' package is key.

from . import (
    lily_cmds,  # Add this line
    ner_cmds,  # Assuming you have this for your NER commands
)

# If you use __all__ to define the public interface of this package:
# __all__ = ["ner_cmds", "lily_cmds"] # Add other command modules as needed
