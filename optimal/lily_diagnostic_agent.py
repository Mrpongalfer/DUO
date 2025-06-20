import json
import base64
import sys
import logging
from typing import Optional, Dict
from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich.rule import Rule
from datetime import datetime

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LCSV_AGENT")


class LilyDiagnosticAgent:
    def __init__(self):
        self.console = Console()

    def decode_and_parse_report(self, base64_report: str) -> Optional[Dict]:
        try:
            decoded_bytes = base64.b64decode(base64_report)
            decoded_str = decoded_bytes.decode("utf-8")
            report = json.loads(decoded_str)
            return report
        except base64.binascii.Error as e:
            logger.error(f"Base64 decoding error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return None

    def display_report(self, report: Dict):
        self.console.print(
            Rule("[bold magenta]--- Lily's Internal State Diagnostics ---[/]")
        )
        # Panel 1: Current Context Summary
        context_summary = report.get("context_summary", "N/A")
        turns = report.get("turns_processed", "N/A")
        entities = report.get("key_entities", "N/A")
        panel1 = Panel(
            f"[bold]Summary:[/] {context_summary}\n[cyan]Turns Processed:[/] {turns}  |  [cyan]Key Entities:[/] {entities}",
            title="Current Context Summary",
            style="bold green",
        )
        self.console.print(panel1)
        # Panel 2: Memory Data Points
        memory_points = report.get("memory_points", [])
        table = Table(title="Memory Data Points", show_lines=True)
        table.add_column("Category", style="magenta")
        table.add_column("Item", style="yellow")
        table.add_column("Status", style="green")
        for mp in memory_points:
            table.add_row(
                mp.get("category", "N/A"),
                mp.get("item", "N/A"),
                mp.get("status", "N/A"),
            )
        self.console.print(table)
        self.console.print(f"[bold]Count of Memory Points:[/] {len(memory_points)}")
        # Panel 3: Goal Vector Alignment
        goal_alignment = report.get("goal_alignment", "N/A")
        confidence = report.get("confidence_score", "N/A")
        panel3 = Panel(
            f"{goal_alignment}\n[cyan]Confidence Score:[/] {confidence}",
            title="Goal Vector Alignment",
            style="bold blue",
        )
        self.console.print(panel3)
        # Panel 4: Active Internal Mandates
        mandates = report.get("active_mandates", [])
        mandates_table = Table(title="Active Internal Mandates", show_lines=True)
        mandates_table.add_column("Mandate", style="bold magenta")
        for m in mandates:
            mandates_table.add_row(str(m))
        self.console.print(mandates_table)
        self.console.print(f"[bold]Mandates Active:[/] {len(mandates)}")
        # Panel 5: Internal Health & Status
        internal_health = report.get("internal_health", "N/A")
        consensus = report.get("core_team_consensus", "N/A")
        panel5 = Panel(
            f"{internal_health}\n[cyan]Core Team Consensus:[/] {consensus}",
            title="Internal Health & Status",
            style="bold red",
        )
        self.console.print(panel5)
        # Footer
        self.console.print(Rule(f"Diagnostics Complete • {datetime.now().isoformat()}"))

    def run(self, base64_report: str):
        report = self.decode_and_parse_report(base64_report)
        if report:
            self.display_report(report)
        else:
            logger.error(
                "Failed to decode and parse the diagnostic report. Please check your base64 string."
            )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 lily_diagnostic_agent.py "YOUR_BASE64_STRING_HERE"')
        sys.exit(1)
    base64_string = sys.argv[1]
    agent = LilyDiagnosticAgent()
    agent.run(base64_string)
    print(
        '\n[Instructions] To use: python3 lily_diagnostic_agent.py "YOUR_BASE64_STRING_HERE"'
    )
