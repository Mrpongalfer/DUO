import subprocess
import sys
import os


def run_cmd(cmd, desc):
    print(f"\n=== {desc} ===")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"FAILED: {desc}")
        sys.exit(result.returncode)
    print(f"SUCCESS: {desc}")


if __name__ == "__main__":
    # 1. Lint and format
    run_cmd("black --check .", "Black Formatting Check")
    run_cmd("ruff check .", "Ruff Lint")
    run_cmd("flake8 .", "Flake8 Lint")

    # 2. Scribe Validation
    run_cmd(
        "python3 scribe0.py . --review-only --log-level INFO > scribe_report.json",
        "Scribe Agent Validation",
    )

    # 3. Vector Alignment
    run_cmd("python3 vectorize_constitution.py", "Generate/Update Goal Vectors")
    run_cmd(
        "python3 scripts/check_alignment.py --input scribe_report.json --vectors goal_vectors/ > alignment_score.txt",
        "Vector Alignment Check",
    )

    # 4. Ex-Work Agent
    run_cmd(
        "python3 exworkagent0.py --mode ci --plan-file ci_plan.json --log-level INFO > exwork_output.log",
        "Ex-Work Agent Run",
    )

    # 5. Metamorphosis (Self-Improvement Loop)
    if os.path.exists("metamorphosis.sh"):
        run_cmd("bash metamorphosis.sh", "Metamorphosis Self-Improvement Loop")
    else:
        print("Metamorphosis script not found, skipping...")

    print("\n=== DUO LOCAL PIPELINE COMPLETE ===")
