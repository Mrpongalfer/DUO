"""
Quality Service: Code quality checking and testing.

Provides services for running linters and tests to ensure code quality.
"""

import os
import subprocess
import tempfile
import json
import re
from typing import Any, Dict, List

from quantum_orchestrator.utils.logging_utils import get_logger

logger = get_logger(__name__)


def run_linter_service(
    code: str = "",
    path: str = "",
    linter: str = "flake8",
    fix: bool = False,
    config: Dict[str, Any] = {},
) -> Dict[str, Any]:
    """
    Run a linter on code or files.

    Args:
        code: Code to lint
        path: Path to file or directory to lint
        linter: Linter to use (flake8, black)
        fix: Whether to fix issues automatically
        config: Linter configuration

    Returns:
        Dict containing linting results
    """
    # Validate input
    if not code and not path:
        return {"success": False, "error": "Either code or path must be provided"}

    # Select linter
    linter = linter.lower()
    if linter not in ["flake8", "black"]:
        return {"success": False, "error": f"Unsupported linter: {linter}"}

    # Create a temporary file if code is provided
    if code:
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".py", mode="w", delete=False
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            path = tmp_path
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create temporary file: {str(e)}",
            }

    try:
        # Run the appropriate linter
        if linter == "flake8":
            return _run_flake8(path, config)
        elif linter == "black":
            return _run_black(path, fix, config)

    finally:
        # Clean up temporary file
        if code and "tmp_path" in locals():
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return {"success": False, "error": "Unknown error in linter service"}


def _run_flake8(path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run flake8 on a file or directory.

    Args:
        path: Path to lint
        config: Flake8 configuration

    Returns:
        Dict containing flake8 results
    """
    # Build command
    cmd = ["flake8", path, "--format=json"]

    # Add config options
    max_line_length = config.get("max_line_length")
    if max_line_length:
        cmd.append(f"--max-line-length={max_line_length}")

    ignore = config.get("ignore")
    if ignore:
        if isinstance(ignore, list):
            ignore = ",".join(ignore)
        cmd.append(f"--ignore={ignore}")

    # Run flake8
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output
        issues = []
        if result.stdout:
            try:
                flake8_issues = json.loads(result.stdout)
                for file_path, file_issues in flake8_issues.items():
                    for issue in file_issues:
                        issues.append(
                            {
                                "path": file_path,
                                "line": issue["line_number"],
                                "column": issue["column_number"],
                                "code": issue["code"],
                                "message": issue["text"],
                            }
                        )
            except json.JSONDecodeError:
                # Fallback to line parsing
                for line in result.stdout.splitlines():
                    match = re.match(r"(.+):(\d+):(\d+): (\w+) (.*)", line)
                    if match:
                        issues.append(
                            {
                                "path": match.group(1),
                                "line": int(match.group(2)),
                                "column": int(match.group(3)),
                                "code": match.group(4),
                                "message": match.group(5),
                            }
                        )

        # Build summary
        summary = {
            "issues_count": len(issues),
            "files_checked": (
                len(set(issue["path"] for issue in issues)) if issues else 1
            ),
            "exit_code": result.returncode,
        }

        return {
            "success": result.returncode == 0,
            "issues": issues,
            "summary": summary,
            "fixed_code": None,  # Flake8 doesn't fix code
        }

    except Exception as e:
        logger.error(f"Error running flake8: {str(e)}")
        return {"success": False, "error": f"Error running flake8: {str(e)}"}


def _run_black(path: str, fix: bool, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run black on a file or directory.

    Args:
        path: Path to lint/format
        fix: Whether to fix issues
        config: Black configuration

    Returns:
        Dict containing black results
    """
    # Build command for check mode
    cmd = ["black"]

    # Add config options
    line_length = config.get("line_length")
    if line_length:
        cmd.append(f"--line-length={line_length}")

    # Read code before formatting
    original_code = None
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                original_code = f.read()
        except Exception:
            pass

    # Check mode (don't modify files)
    if not fix:
        cmd.append("--check")

    cmd.append("--verbose")
    cmd.append(path)

    # Run black
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Build issues list
        issues = []
        for line in result.stdout.splitlines():
            if "would reformat" in line or "reformatted" in line:
                file_path = line.split()[-1]
                issues.append(
                    {
                        "path": file_path,
                        "line": 0,
                        "column": 0,
                        "code": "BLACK",
                        "message": "File needs formatting",
                    }
                )

        # Get formatted code if fix was enabled
        fixed_code = None
        if fix and original_code is not None:
            try:
                with open(path, "r") as f:
                    fixed_code = f.read()
            except Exception:
                pass

        # Build summary
        summary = {
            "issues_count": len(issues),
            "files_checked": result.stdout.count(
                "would reformat" if not fix else "reformatted"
            )
            + result.stdout.count("already well formatted"),
            "exit_code": result.returncode,
        }

        return {
            "success": result.returncode == 0,
            "issues": issues,
            "summary": summary,
            "fixed_code": fixed_code,
        }

    except Exception as e:
        logger.error(f"Error running black: {str(e)}")
        return {"success": False, "error": f"Error running black: {str(e)}"}


def run_tests_service(
    path: str,
    pattern: str = "test_*.py",
    framework: str = "pytest",
    verbosity: int = 2,
    args: List[str] = [],
) -> Dict[str, Any]:
    """
    Run tests in a specified path.

    Args:
        path: Path to directory or file to test
        pattern: Test file pattern
        framework: Test framework (pytest, unittest)
        verbosity: Verbosity level
        args: Additional arguments for the test command

    Returns:
        Dict containing test results
    """
    # Validate framework
    framework = framework.lower()
    if framework not in ["pytest", "unittest"]:
        return {"success": False, "error": f"Unsupported test framework: {framework}"}

    # Run the appropriate test framework
    if framework == "pytest":
        return _run_pytest(path, pattern, verbosity, args)
    elif framework == "unittest":
        return _run_unittest(path, pattern, verbosity, args)

    return {"success": False, "error": "Unknown error in test service"}


def _run_pytest(
    path: str, pattern: str, verbosity: int, args: List[str]
) -> Dict[str, Any]:
    """
    Run pytest on a file or directory.

    Args:
        path: Path to test
        pattern: Test file pattern
        verbosity: Verbosity level
        args: Additional arguments

    Returns:
        Dict containing pytest results
    """
    # Build command
    cmd = ["pytest"]

    # Add verbosity
    if verbosity > 0:
        cmd.append(f"-{'v' * min(verbosity, 3)}")

    # Add JSON output
    cmd.append("--json-report")
    cmd.append("--json-report-file=none")

    # Add pattern
    if pattern:
        cmd.append("-k")
        cmd.append(pattern)

    # Add custom args
    cmd.extend(args)

    # Add path
    cmd.append(path)

    # Run pytest
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output
        # Since we're using --json-report-file=none, the JSON is printed to stdout
        json_start = result.stdout.find("{")
        json_end = result.stdout.rfind("}")

        if json_start >= 0 and json_end >= 0:
            json_output = result.stdout[json_start : json_end + 1]
            try:
                report = json.loads(json_output)

                # Extract test results
                test_results = []
                for test_id, test_data in report.get("tests", {}).items():
                    test_results.append(
                        {
                            "id": test_id,
                            "name": test_data.get("name"),
                            "outcome": test_data.get("outcome"),
                            "message": (
                                test_data.get("call", {}).get("longrepr", "")
                                if test_data.get("outcome") != "passed"
                                else ""
                            ),
                        }
                    )

                # Build summary
                summary = {
                    "total": report.get("summary", {}).get("total", 0),
                    "passed": report.get("summary", {}).get("passed", 0),
                    "failed": report.get("summary", {}).get("failed", 0),
                    "skipped": report.get("summary", {}).get("skipped", 0),
                    "duration": report.get("duration", 0),
                }

                return {
                    "success": summary["failed"] == 0,
                    "results": test_results,
                    "summary": summary,
                    "output": result.stdout,
                }

            except json.JSONDecodeError:
                pass

        # Fallback to parsing stdout
        test_results = []
        total = 0
        passed = 0
        failed = 0
        skipped = 0

        # Simple regex parsing for test results
        for line in result.stdout.splitlines():
            if line.startswith("test_"):
                total += 1
                if " PASSED " in line:
                    passed += 1
                    test_results.append(
                        {
                            "id": line.split()[0],
                            "name": line.split()[0],
                            "outcome": "passed",
                            "message": "",
                        }
                    )
                elif " FAILED " in line:
                    failed += 1
                    test_results.append(
                        {
                            "id": line.split()[0],
                            "name": line.split()[0],
                            "outcome": "failed",
                            "message": "Test failed",
                        }
                    )
                elif " SKIPPED " in line:
                    skipped += 1
                    test_results.append(
                        {
                            "id": line.split()[0],
                            "name": line.split()[0],
                            "outcome": "skipped",
                            "message": "Test skipped",
                        }
                    )

        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": 0,  # Can't determine without JSON output
        }

        return {
            "success": failed == 0,
            "results": test_results,
            "summary": summary,
            "output": result.stdout,
        }

    except Exception as e:
        logger.error(f"Error running pytest: {str(e)}")
        return {"success": False, "error": f"Error running pytest: {str(e)}"}


def _run_unittest(
    path: str, pattern: str, verbosity: int, args: List[str]
) -> Dict[str, Any]:
    """
    Run unittest on a file or directory.

    Args:
        path: Path to test
        pattern: Test file pattern
        verbosity: Verbosity level
        args: Additional arguments

    Returns:
        Dict containing unittest results
    """
    # Build command
    cmd = ["python", "-m", "unittest", "discover"]

    # Add verbosity
    cmd.append("-v")

    # Add pattern
    if pattern:
        cmd.append("-p")
        cmd.append(pattern)

    # Add start directory
    cmd.append("-s")
    cmd.append(path)

    # Add custom args
    cmd.extend(args)

    # Run unittest
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output
        test_results = []
        total = 0
        passed = 0
        failed = 0
        skipped = 0

        # Simple regex parsing for test results
        for line in result.stdout.splitlines():
            if re.match(r".+\s\.\.\.\s", line):
                total += 1
                test_name = line.split(" ... ")[0].strip()
                if " ... ok" in line:
                    passed += 1
                    test_results.append(
                        {
                            "id": test_name,
                            "name": test_name,
                            "outcome": "passed",
                            "message": "",
                        }
                    )
                elif " ... FAIL" in line:
                    failed += 1
                    test_results.append(
                        {
                            "id": test_name,
                            "name": test_name,
                            "outcome": "failed",
                            "message": "Test failed",
                        }
                    )
                elif " ... skipped" in line:
                    skipped += 1
                    test_results.append(
                        {
                            "id": test_name,
                            "name": test_name,
                            "outcome": "skipped",
                            "message": "Test skipped",
                        }
                    )

        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": 0,  # Can't determine from unittest output
        }

        return {
            "success": failed == 0,
            "results": test_results,
            "summary": summary,
            "output": result.stdout,
        }

    except Exception as e:
        logger.error(f"Error running unittest: {str(e)}")
        return {"success": False, "error": f"Error running unittest: {str(e)}"}
