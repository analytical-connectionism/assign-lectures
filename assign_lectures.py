#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "matching",
#     "rich",
# ]
# ///

import csv
import sys
import warnings
from typing import Dict, List, Any
import click
from matching.games import HospitalResident
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

warnings.filterwarnings("ignore", category=UserWarning, module="matching")

console = Console()


def load_scribe_preferences(csv_file: str) -> Dict[str, List[str]]:
    """Load scribe preferences from CSV file."""
    scribe_prefs = {}

    with open(csv_file, "r", newline="") as file:
        reader = csv.reader(file)
        header = next(reader)  # Skip header row

        for row_idx, row in enumerate(reader):
            if not row or not row[0].strip():  # Skip empty rows
                continue

            scribe_id = row[0].strip()
            preferences = []

            # Get preferences from remaining columns (skip empty cells)
            for pref in row[1:]:
                if pref and pref.strip():
                    preferences.append(pref.strip())

            if preferences:  # Only add if scribe has at least one preference
                scribe_prefs[scribe_id] = preferences

    return scribe_prefs


def load_lecturer_preferences(csv_file: str) -> Dict[str, List[str]]:
    """Load lecturer preferences from CSV file."""
    lecturer_prefs = {}

    with open(csv_file, "r", newline="") as file:
        reader = csv.reader(file)
        header = next(reader)  # Skip header row

        for row_idx, row in enumerate(reader):
            if not row or not row[0].strip():  # Skip empty rows
                continue

            lecturer_id = row[0].strip()
            preferences = []

            # Get preferences from remaining columns (skip empty cells)
            for pref in row[1:]:
                if pref and pref.strip():
                    preferences.append(pref.strip())

            if preferences:  # Only add if lecturer has at least one preference
                lecturer_prefs[lecturer_id] = preferences

    return lecturer_prefs


def load_lecturer_quotas(csv_file: str) -> Dict[str, int]:
    """Load lecturer quotas from CSV file."""
    quotas = {}

    with open(csv_file, "r", newline="") as file:
        reader = csv.reader(file)
        header = next(reader)  # Skip header row

        for row_idx, row in enumerate(reader):
            if not row or len(row) < 2:  # Skip empty or invalid rows
                continue

            lecturer_name = row[0].strip()
            try:
                quota = int(row[1].strip())
                quotas[lecturer_name] = quota
            except ValueError:
                print(
                    f"Warning: Invalid quota '{row[1]}' for lecturer '{lecturer_name}' on row {row_idx + 2}"
                )
                continue

    return quotas


def get_lecturer_quotas() -> Dict[str, int]:
    """Get lecturer quotas via interactive input."""
    print("Enter lecturer quotas (lecturer_name:quota). Press Enter twice when done:")
    quotas = {}

    while True:
        line = input().strip()
        if not line:
            break

        try:
            lecturer, quota_str = line.split(":")
            quota = int(quota_str.strip())
            quotas[lecturer.strip()] = quota
        except (ValueError, IndexError):
            print("Invalid format. Use 'lecturer_name:quota' (e.g., 'Prof_Smith:3')")

    return quotas


def solve_matching_with_minimum_allocation(
    scribe_prefs: Dict[str, List[str]],
    lecturer_prefs: Dict[str, List[str]],
    lecturer_quotas: Dict[str, int],
    quiet: bool = False,
) -> Any:
    """Solve matching using standard Gale-Shapley algorithm."""
    game = HospitalResident.create_from_dictionaries(
        scribe_prefs, lecturer_prefs, lecturer_quotas
    )
    return game.solve()


def create_lecturer_preferences(
    scribes: List[str], lecturers: List[str]
) -> Dict[str, List[str]]:
    """Create uniform lecturer preferences for all scribes."""
    lecturer_prefs = {}

    # All lecturers have identical preference lists (all scribes in same order)
    # The order doesn't matter since they're indifferent, but we need some order
    all_scribes = sorted(scribes)

    for lecturer in lecturers:
        # Each lecturer is willing to accept any scribe (uniform preferences)
        lecturer_prefs[lecturer] = all_scribes.copy()

    return lecturer_prefs


def print_matching_results(matching: Any, all_scribes: List[str]):
    """Display matching results in formatted tables."""
    console.print()

    # Create main results table
    table = Table(
        title="🎓 Scribe-Lecturer Assignments",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Lecturer", style="cyan", no_wrap=True)
    table.add_column("Assigned Scribes", style="green")
    table.add_column("Count", justify="center", style="yellow")

    # The matching object maps lecturers to lists of scribes
    lecturer_assignments = dict(matching)
    all_matched_scribes = set()

    # Sort lecturers by name and add to table
    for lecturer in sorted(lecturer_assignments.keys(), key=str):
        lecturer_name = str(lecturer)
        assigned_scribes = lecturer_assignments[lecturer]
        scribe_names = [str(scribe) for scribe in assigned_scribes]
        all_matched_scribes.update(scribe_names)

        scribes_str = ", ".join(sorted(scribe_names)) if scribe_names else "None"
        table.add_row(lecturer_name, scribes_str, str(len(scribe_names)))

    console.print(table)

    # Summary statistics
    unmatched_scribes = set(all_scribes) - all_matched_scribes

    summary_table = Table(
        title="📊 Summary Statistics", show_header=True, header_style="bold blue"
    )
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", justify="center", style="yellow")

    summary_table.add_row("Total Scribes", str(len(all_scribes)))
    summary_table.add_row("Matched Scribes", str(len(all_matched_scribes)))
    summary_table.add_row("Unmatched Scribes", str(len(unmatched_scribes)))
    summary_table.add_row("Total Lecturers", str(len(lecturer_assignments)))

    console.print()
    console.print(summary_table)

    # Show unmatched scribes if any
    if unmatched_scribes:
        console.print()
        unmatched_table = Table(
            title="❌ Unmatched Scribes", show_header=True, header_style="bold red"
        )
        unmatched_table.add_column("Scribe", style="red")

        for scribe in sorted(unmatched_scribes):
            unmatched_table.add_row(scribe)

        console.print(unmatched_table)


@click.command()
@click.argument("scribe_preferences", type=click.Path(exists=True))
@click.option(
    "--lecturer-preferences",
    "-p",
    type=click.Path(exists=True),
    help="CSV file with lecturer preferences (optional)",
)
@click.option(
    "--lecturer-quotas",
    "-q",
    type=click.Path(exists=True),
    help="CSV file with lecturer quotas (optional)",
)
@click.option("--quiet", is_flag=True, help="Only show final results")
@click.help_option("--help", "-h")
def main(
    scribe_preferences: str,
    lecturer_preferences: str | None = None,
    lecturer_quotas: str | None = None,
    quiet: bool = False,
):
    """Assign scribes to lecturers using stable matching.

    Ensures each lecturer gets at least 1 scribe. Uses Gale-Shapley algorithm
    with uniform lecturer preferences when no preferences file provided.

    Required CSV formats:
        scribe_preferences.csv: scribe_name,1st_choice,2nd_choice,...
        lecturer_quotas.csv: lecturer_name,quota
        lecturer_preferences.csv: lecturer_name,1st_choice,2nd_choice,...
    """

    try:
        # Load scribe preferences
        if not quiet:
            console.print(
                f"📋 [bold blue]Loading scribe preferences from[/bold blue] [cyan]{scribe_preferences}[/cyan]..."
            )
        scribe_prefs = load_scribe_preferences(scribe_preferences)

        if not scribe_prefs:
            console.print(
                "[bold red]❌ No valid scribe preferences found in CSV file.[/bold red]"
            )
            sys.exit(1)

        if not quiet:
            console.print(
                f"✅ [green]Loaded preferences for[/green] [bold]{len(scribe_prefs)}[/bold] [green]scribes[/green]"
            )

        # Get all unique lecturers mentioned in scribe preferences
        all_lecturers = set()
        for prefs in scribe_prefs.values():
            all_lecturers.update(prefs)
        all_lecturers = sorted(list(all_lecturers))

        if not quiet:
            console.print(
                f"🎓 [blue]Found[/blue] [bold]{len(all_lecturers)}[/bold] [blue]lecturers:[/blue] [dim]{', '.join(all_lecturers)}[/dim]"
            )

        # Load lecturer quotas
        if lecturer_quotas:
            if not quiet:
                console.print(
                    f"📊 [bold blue]Loading lecturer quotas from[/bold blue] [cyan]{lecturer_quotas}[/cyan]..."
                )
            lecturer_quota_dict = load_lecturer_quotas(lecturer_quotas)
        else:
            if not quiet:
                console.print(
                    "⌨️  [yellow]No lecturer quotas file provided. Getting quotas via user input...[/yellow]"
                )
            lecturer_quota_dict = get_lecturer_quotas()

        if not lecturer_quota_dict:
            console.print(
                "[bold red]❌ No lecturer quotas provided. Exiting.[/bold red]"
            )
            sys.exit(1)

        # Validate that all lecturers have quotas
        missing_quotas = set(all_lecturers) - set(lecturer_quota_dict.keys())
        if missing_quotas:
            if not quiet:
                console.print(
                    f"⚠️  [yellow]Warning: No quotas provided for lecturers:[/yellow] [dim]{', '.join(missing_quotas)}[/dim]"
                )
                console.print("[yellow]Setting their quotas to 1...[/yellow]")
            for lecturer in missing_quotas:
                lecturer_quota_dict[lecturer] = 1

        # Load or create lecturer preferences
        scribes = list(scribe_prefs.keys())
        if lecturer_preferences:
            if not quiet:
                console.print(
                    f"👥 [bold blue]Loading lecturer preferences from[/bold blue] [cyan]{lecturer_preferences}[/cyan]..."
                )
            lecturer_prefs = load_lecturer_preferences(lecturer_preferences)

            # Validate that all lecturers in quotas have preferences
            missing_lecturer_prefs = set(lecturer_quota_dict.keys()) - set(
                lecturer_prefs.keys()
            )
            if missing_lecturer_prefs:
                if not quiet:
                    console.print(
                        f"⚠️  [yellow]Warning: No preferences found for lecturers:[/yellow] [dim]{', '.join(missing_lecturer_prefs)}[/dim]"
                    )
                    console.print(
                        "[yellow]Creating uniform preferences for them...[/yellow]"
                    )
                uniform_prefs = create_lecturer_preferences(
                    scribes, list(missing_lecturer_prefs)
                )
                lecturer_prefs.update(uniform_prefs)
        else:
            if not quiet:
                console.print(
                    "🎲 [yellow]No lecturer preferences file provided. Creating uniform preferences...[/yellow]"
                )
            lecturer_prefs = create_lecturer_preferences(
                scribes, list(lecturer_quota_dict.keys())
            )

        # Create and solve the matching game with minimum allocation constraint
        if not quiet:
            console.print(
                "\n🧮 [bold magenta]Solving matching problem...[/bold magenta]"
            )
            with console.status("[bold green]Computing stable matching...") as status:
                matching = solve_matching_with_minimum_allocation(
                    scribe_prefs, lecturer_prefs, lecturer_quota_dict, quiet
                )
            console.print("✅ [bold green]Matching completed![/bold green]")
        else:
            matching = solve_matching_with_minimum_allocation(
                scribe_prefs, lecturer_prefs, lecturer_quota_dict, quiet
            )

        # Display results
        print_matching_results(matching, scribes)

    except FileNotFoundError as e:
        console.print(f"[bold red]❌ Error: File not found - {e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
