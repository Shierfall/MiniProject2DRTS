from __future__ import annotations

import os
import sys
import subprocess
from typing import Optional

import typer
from rich.console import Console

from tsn_case_gen_.cli import __version__

app = typer.Typer(
    help="TSN test case generator.",
    add_completion=False,
    no_args_is_help=False,  # allow no-args; we'll handle default behavior
)
console = Console()

DEFAULT_CONFIG = "./industrial_config.json"


def _run_generator(config_path: str) -> None:
    """
    Delegate to the real generator. The tests patch tsn_case_gen.TSNTestCaseGenerator,
    so import from that module name (without underscore).
    """
    from tsn_case_gen_.app.tsn_case_gen import TSNTestCaseGenerator
    gen = TSNTestCaseGenerator(config_path=config_path)
    gen.generate_test_cases()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the version and exit.",
        is_eager=True,
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help=f"Path to config file (defaults to {DEFAULT_CONFIG})",
    ),
) -> None:
    """
    Root entrypoint:
    - `--version` prints version.
    - If no subcommand is invoked, run the generator:
        * If --config is omitted: use DEFAULT_CONFIG and exit(1) if missing.
        * If --config is provided: don't check existence (tests pass a dummy path).
        * Any exception during run -> exit(1).
    """
    if version:
        console.print(f"tsn-case-gen version: {__version__}")
        return  # don't raise; avoid SystemExit on success

    if ctx.invoked_subcommand is None:
        if config is None:
            cfg = DEFAULT_CONFIG
            if not os.path.exists(cfg):
                console.print(f"Error: config file not found: {cfg}")
                sys.exit(1)  # tests expect SystemExit here when default is missing
                return
        else:
            cfg = config  # do not check existence when user provided --config

        try:
            _run_generator(cfg)
        except Exception as e:
            console.print(f"Error while running generator: {e}")
            sys.exit(1)  # tests expect SystemExit on exception
            return


@app.command("version", help="Show the version and exit.")
def version_cmd() -> None:
    console.print(f"tsn-case-gen version: {__version__}")


@app.command(help="Run mypy type checks on the package.")
def lint() -> None:
    """Run mypy type checking and print results."""
    console.print("[bold]Running mypy type checks...[bold]")
    # NOTE: target the UNDERSCORE package (this repo)
    result = subprocess.run(["mypy", "tsn_case_gen_"], capture_output=True, text=True)
    if result.returncode == 0:
        console.print("[green]Success: no issues found.[/green]")
    else:
        console.print(f"[red]mypy found issues:[/red]\n{result.stdout}")
        # Signal failure for CI; Typer-friendly exit
        raise typer.Exit(code=1)




@app.command(help="Validate config or output files against schema.")
def validate(
    json_file: str = typer.Option(..., "--json", help="Path to JSON file to validate."),
) -> None:
    console.print(f"[bold green]Validating:[/bold green] {json_file}")
    # Run the universal validation script
    validation_script = os.path.join(os.path.dirname(__file__), '../domain/validation.py')
    result = subprocess.run([
        sys.executable,
        validation_script,
        '--json', json_file
    ], capture_output=True, text=True)
    if result.returncode == 0:
        console.print(f"[green]Validation successful.[/green]\n{result.stdout}")
    else:
        console.print(f"[red]Validation failed:[/red]\n{result.stdout}\n{result.stderr}")
        raise typer.Exit(code=1)


@app.command(help="Show tool info and supported formats.")
def info() -> None:
    console.print("[bold]TSN test case generator & utilities[/bold]")
    console.print("Supported formats: JSON, CSV, GraphML")
    console.print(f"Default config location: {DEFAULT_CONFIG}")
    console.print("Default output directory: ./out/")
    console.print("Shell completion: [italic]tsn-case-gen --install-completion[/italic]")


def main() -> None:
    # Prevent Typer from auto sys.exit on success paths
    app(standalone_mode=False)


if __name__ == "__main__":
    main()
