# Ex-Work Agent Interface Notes

- Expects JSON instruction block via stdin.
- Outputs JSON result to stdout.
- Key action types: ECHO, CREATE_OR_REPLACE_FILE, RUN_SCRIPT, LINT_FORMAT_FILE, GIT_ADD, GIT_COMMIT, CALL_LOCAL_LLM, DIAGNOSE_ERROR, APPLY_PATCH, REQUEST_SIGNOFF.