"""Command-line interface for Trading 212 to GnuCash converter.

Copyright (C) 2025 Tim Waugh

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import __version__
from .config import Config, create_sample_config
from .converter import Trading212Converter

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Set up rich logging."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def cli(ctx: click.Context, version: bool) -> None:
    """Trading 212 to GnuCash converter.

    A modern Python tool to convert Trading 212 CSV exports into a format
    suitable for GnuCash multi-split import.
    """
    if version:
        click.echo(f"trading212-gnucash {__version__}")
        ctx.exit()

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option(
    "--validate-only", is_flag=True, help="Only validate the input file, don't convert"
)
def convert(
    input_file: Path,
    output_file: Path,
    config: Optional[Path],
    verbose: bool,
    validate_only: bool,
) -> None:
    """Convert Trading 212 CSV file to GnuCash format.

    INPUT_FILE: Path to the Trading 212 CSV export file
    OUTPUT_FILE: Path for the GnuCash-compatible CSV output
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        if config:
            app_config = Config.load_from_file(config)
            logger.info(f"Loaded configuration from {config}")
        else:
            app_config = Config.load_from_file()
            logger.info("Using default configuration")

        # Initialize converter
        converter = Trading212Converter(app_config)

        # Validate input file
        console.print(f"[blue]Validating input file:[/blue] {input_file}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Validating CSV format...", total=None)

            if not converter.validate_csv_file(input_file):
                console.print("[red]❌ Input file validation failed[/red]")
                sys.exit(1)

            progress.update(task, description="✅ CSV format valid")

        if validate_only:
            console.print("[green]✅ Input file is valid[/green]")
            return

        # Convert file
        console.print(f"[blue]Converting to:[/blue] {output_file}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Converting transactions...", total=None)

            success = converter.convert_file(input_file, output_file)

            if success:
                progress.update(task, description="✅ Conversion completed")
                console.print(
                    f"[green]✅ Successfully converted to {output_file}[/green]"
                )
            else:
                progress.update(task, description="❌ Conversion failed")
                console.print("[red]❌ Conversion failed[/red]")
                sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(path_type=Path),
    default=Path("~/.config/trading212-gnucash/config.yaml").expanduser(),
    help="Configuration file path to create",
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration file")
def init_config(config: Path, force: bool) -> None:
    """Create a sample configuration file.

    This creates a YAML configuration file with default settings that you can
    customize for your needs.
    """
    setup_logging()

    if config.exists() and not force:
        console.print(f"[yellow]Configuration file already exists: {config}[/yellow]")
        console.print("Use --force to overwrite")
        return

    try:
        create_sample_config(config)
        console.print(f"[green]✅ Sample configuration created: {config}[/green]")
        console.print("\n[blue]Next steps:[/blue]")
        console.print("1. Edit the configuration file to customize ticker mappings")
        console.print("2. Update account names to match your GnuCash setup")
        if config == Path("~/.config/trading212-gnucash/config.yaml").expanduser():
            console.print(
                "3. Run: [bold]trading212-gnucash convert input.csv output.csv[/bold]"
            )
            console.print("   (Configuration will be loaded automatically)")
        else:
            console.print(
                f"3. Run: [bold]trading212-gnucash convert input.csv output.csv -c {config}[/bold]"
            )

    except Exception as e:
        console.print(f"[red]❌ Error creating configuration: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file to validate",
)
def validate_config(config: Optional[Path]) -> None:
    """Validate configuration file.

    Check that the configuration file is valid and display current settings.
    """
    setup_logging()

    try:
        if config:
            app_config = Config.load_from_file(config)
            console.print(f"[green]✅ Configuration file is valid: {config}[/green]")
        else:
            app_config = Config.load_from_file()
            console.print("[green]✅ Default configuration loaded[/green]")

        # Display configuration summary
        table = Table(title="Configuration Summary")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Ticker Mappings", str(len(app_config.ticker_map)))
        table.add_row("Deposit Account", app_config.deposit_account)
        table.add_row("Interest Account", app_config.interest_account)
        table.add_row(
            "Conversion Fee Account", app_config.expense_accounts.conversion_fee
        )
        table.add_row("French Tax Account", app_config.expense_accounts.french_tax)
        table.add_row("Stamp Duty Account", app_config.expense_accounts.stamp_duty_tax)

        console.print(table)

        if app_config.ticker_map:
            ticker_table = Table(title="Ticker Mappings")
            ticker_table.add_column("Trading 212", style="yellow")
            ticker_table.add_column("GnuCash Symbol", style="green")

            for t212, gnucash_symbol in sorted(app_config.ticker_map.items()):
                ticker_table.add_row(t212, gnucash_symbol)

            console.print(ticker_table)

    except Exception as e:
        console.print(f"[red]❌ Configuration error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
def info(input_file: Path) -> None:
    """Display information about a Trading 212 CSV file.

    INPUT_FILE: Path to the Trading 212 CSV export file
    """
    setup_logging()

    try:
        converter = Trading212Converter()

        if not converter.validate_csv_file(input_file):
            console.print("[red]❌ Invalid CSV file[/red]")
            sys.exit(1)

        # Analyze the file
        console.print(f"[blue]Analyzing:[/blue] {input_file}")

        transactions = list(converter.read_transactions(input_file))

        if not transactions:
            console.print("[yellow]No transactions found[/yellow]")
            return

        # Summary statistics
        action_counts: dict[str, int] = {}
        ticker_counts: dict[str, int] = {}
        date_range = []

        for transaction in transactions:
            action_counts[transaction.action] = (
                action_counts.get(transaction.action, 0) + 1
            )

            if transaction.ticker:
                ticker_counts[transaction.ticker] = (
                    ticker_counts.get(transaction.ticker, 0) + 1
                )

            date_range.append(transaction.time)

        # Display summary
        summary_table = Table(title="File Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Total Transactions", str(len(transactions)))
        summary_table.add_row("Unique Tickers", str(len(ticker_counts)))
        if date_range:
            summary_table.add_row(
                "Date Range", f"{min(date_range)} to {max(date_range)}"
            )

        console.print(summary_table)

        # Action types
        if action_counts:
            action_table = Table(title="Transaction Types")
            action_table.add_column("Action", style="yellow")
            action_table.add_column("Count", style="green")

            for action, count in sorted(action_counts.items()):
                action_table.add_row(action, str(count))

            console.print(action_table)

        # Top tickers
        if ticker_counts:
            ticker_table = Table(title="Top Tickers")
            ticker_table.add_column("Ticker", style="yellow")
            ticker_table.add_column("Transactions", style="green")

            for ticker, count in sorted(
                ticker_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                ticker_table.add_row(ticker, str(count))

            console.print(ticker_table)

    except Exception as e:
        console.print(f"[red]❌ Error analyzing file: {e}[/red]")
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
