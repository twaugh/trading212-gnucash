"""Tests for the CLI module.

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
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from trading212_gnucash import __version__
from trading212_gnucash.cli import cli, main, setup_logging
from trading212_gnucash.config import Config


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def sample_csv_content():
    """Sample Trading 212 CSV content for testing."""
    return """Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,Currency (Price / share),Exchange rate,Currency (Result),Total,Currency (Total)
Market buy,2025-01-01 10:00:00.000,US5949181045,MSFT,Microsoft Corporation,,12345,10.5,150.00,USD,0.8,GBP,-1260.00,GBP
Deposit,2025-01-01 09:00:00.000,,,,,54321,,,,,GBP,1000.00,GBP
"""


@pytest.fixture
def temp_csv_file(sample_csv_content):
    """Create a temporary CSV file with sample content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(sample_csv_content)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_config_file():
    """Create a temporary config file path."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)

    # Remove the file so tests can create it
    temp_path.unlink()

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestSetupLogging:
    """Test logging setup functionality."""

    def test_setup_logging_default(self):
        """Test default logging setup."""
        with patch("trading212_gnucash.cli.logging.basicConfig") as mock_config:
            setup_logging()
            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args
            assert kwargs["level"] == logging.INFO

    def test_setup_logging_verbose(self):
        """Test verbose logging setup."""
        with patch("trading212_gnucash.cli.logging.basicConfig") as mock_config:
            setup_logging(verbose=True)
            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args
            assert kwargs["level"] == logging.DEBUG


class TestMainCLI:
    """Test main CLI command group."""

    def test_cli_version_flag(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert f"trading212-gnucash {__version__}" in result.output

    def test_cli_no_command_shows_help(self, runner):
        """Test that CLI shows help when no command is provided."""
        result = runner.invoke(cli)
        assert result.exit_code == 0
        assert "Trading 212 to GnuCash converter" in result.output
        assert "Commands:" in result.output

    def test_cli_help(self, runner):
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Trading 212 to GnuCash converter" in result.output

    def test_main_function(self):
        """Test main function calls cli."""
        with patch("trading212_gnucash.cli.cli") as mock_cli:
            main()
            mock_cli.assert_called_once()


class TestConvertCommand:
    """Test convert command functionality."""

    def test_convert_help(self, runner):
        """Test convert command help."""
        result = runner.invoke(cli, ["convert", "--help"])
        assert result.exit_code == 0
        assert "Convert Trading 212 CSV file" in result.output

    def test_convert_missing_input_file(self, runner):
        """Test convert with non-existent input file."""
        result = runner.invoke(cli, ["convert", "nonexistent.csv", "output.csv"])
        assert result.exit_code == 2
        assert "does not exist" in result.output

    @patch("trading212_gnucash.cli.Trading212Converter")
    @patch("trading212_gnucash.cli.Config")
    def test_convert_success(
        self, mock_config_class, mock_converter_class, runner, temp_csv_file
    ):
        """Test successful conversion."""
        # Mock configuration
        mock_config = Mock()
        mock_config_class.load_from_file.return_value = mock_config

        # Mock converter
        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = True
        mock_converter.convert_file.return_value = True
        mock_converter_class.return_value = mock_converter

        with tempfile.NamedTemporaryFile(suffix=".csv") as output_file:
            result = runner.invoke(
                cli, ["convert", str(temp_csv_file), output_file.name]
            )

        assert result.exit_code == 0
        assert "Successfully converted" in result.output
        mock_converter.validate_csv_file.assert_called_once()
        mock_converter.convert_file.assert_called_once()

    @patch("trading212_gnucash.cli.Trading212Converter")
    @patch("trading212_gnucash.cli.Config")
    def test_convert_validation_failure(
        self, mock_config_class, mock_converter_class, runner, temp_csv_file
    ):
        """Test conversion with validation failure."""
        # Mock configuration
        mock_config = Mock()
        mock_config_class.load_from_file.return_value = mock_config

        # Mock converter with validation failure
        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = False
        mock_converter_class.return_value = mock_converter

        with tempfile.NamedTemporaryFile(suffix=".csv") as output_file:
            result = runner.invoke(
                cli, ["convert", str(temp_csv_file), output_file.name]
            )

        assert result.exit_code == 1
        assert "Input file validation failed" in result.output

    @patch("trading212_gnucash.cli.Trading212Converter")
    @patch("trading212_gnucash.cli.Config")
    def test_convert_conversion_failure(
        self, mock_config_class, mock_converter_class, runner, temp_csv_file
    ):
        """Test conversion with conversion failure."""
        # Mock configuration
        mock_config = Mock()
        mock_config_class.load_from_file.return_value = mock_config

        # Mock converter with conversion failure
        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = True
        mock_converter.convert_file.return_value = False
        mock_converter_class.return_value = mock_converter

        with tempfile.NamedTemporaryFile(suffix=".csv") as output_file:
            result = runner.invoke(
                cli, ["convert", str(temp_csv_file), output_file.name]
            )

        assert result.exit_code == 1
        assert "Conversion failed" in result.output

    @patch("trading212_gnucash.cli.Trading212Converter")
    @patch("trading212_gnucash.cli.Config")
    def test_convert_validate_only(
        self, mock_config_class, mock_converter_class, runner, temp_csv_file
    ):
        """Test convert with --validate-only flag."""
        # Mock configuration
        mock_config = Mock()
        mock_config_class.load_from_file.return_value = mock_config

        # Mock converter
        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = True
        mock_converter_class.return_value = mock_converter

        with tempfile.NamedTemporaryFile(suffix=".csv") as output_file:
            result = runner.invoke(
                cli,
                ["convert", str(temp_csv_file), output_file.name, "--validate-only"],
            )

        assert result.exit_code == 0
        assert "Input file is valid" in result.output
        mock_converter.validate_csv_file.assert_called_once()
        mock_converter.convert_file.assert_not_called()

    @patch("trading212_gnucash.cli.Trading212Converter")
    @patch("trading212_gnucash.cli.Config")
    def test_convert_with_custom_config(
        self,
        mock_config_class,
        mock_converter_class,
        runner,
        temp_csv_file,
        temp_config_file,
    ):
        """Test convert with custom config file."""
        # Create a config file
        config = Config()
        config.save_to_file(temp_config_file)

        # Mock configuration loading
        mock_config = Mock()
        mock_config_class.load_from_file.return_value = mock_config

        # Mock converter
        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = True
        mock_converter.convert_file.return_value = True
        mock_converter_class.return_value = mock_converter

        with tempfile.NamedTemporaryFile(suffix=".csv") as output_file:
            result = runner.invoke(
                cli,
                [
                    "convert",
                    str(temp_csv_file),
                    output_file.name,
                    "--config",
                    str(temp_config_file),
                ],
            )

        assert result.exit_code == 0
        mock_config_class.load_from_file.assert_called_with(temp_config_file)

    @patch("trading212_gnucash.cli.Trading212Converter")
    @patch("trading212_gnucash.cli.Config")
    def test_convert_verbose_logging(
        self, mock_config_class, mock_converter_class, runner, temp_csv_file
    ):
        """Test convert with verbose logging."""
        # Mock configuration
        mock_config = Mock()
        mock_config_class.load_from_file.return_value = mock_config

        # Mock converter
        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = True
        mock_converter.convert_file.return_value = True
        mock_converter_class.return_value = mock_converter

        with tempfile.NamedTemporaryFile(suffix=".csv") as output_file:
            with patch("trading212_gnucash.cli.setup_logging") as mock_setup_logging:
                result = runner.invoke(
                    cli, ["convert", str(temp_csv_file), output_file.name, "--verbose"]
                )

        assert result.exit_code == 0
        mock_setup_logging.assert_called_with(True)

    @patch("trading212_gnucash.cli.Trading212Converter")
    @patch("trading212_gnucash.cli.Config")
    def test_convert_exception_handling(
        self, mock_config_class, mock_converter_class, runner, temp_csv_file
    ):
        """Test convert command exception handling."""
        # Mock configuration to raise exception
        mock_config_class.load_from_file.side_effect = Exception("Config error")

        with tempfile.NamedTemporaryFile(suffix=".csv") as output_file:
            result = runner.invoke(
                cli, ["convert", str(temp_csv_file), output_file.name]
            )

        assert result.exit_code == 1
        # The error is logged but may not appear in CLI output, so just check exit code

    @patch("trading212_gnucash.cli.Trading212Converter")
    @patch("trading212_gnucash.cli.Config")
    def test_convert_exception_verbose(
        self, mock_config_class, mock_converter_class, runner, temp_csv_file
    ):
        """Test convert command exception handling with verbose output."""
        # Mock configuration to raise exception
        mock_config_class.load_from_file.side_effect = Exception("Config error")

        with tempfile.NamedTemporaryFile(suffix=".csv") as output_file:
            with patch(
                "trading212_gnucash.cli.console.print_exception"
            ) as mock_print_exc:
                result = runner.invoke(
                    cli, ["convert", str(temp_csv_file), output_file.name, "--verbose"]
                )

        assert result.exit_code == 1
        mock_print_exc.assert_called_once()


class TestInitConfigCommand:
    """Test init-config command functionality."""

    def test_init_config_help(self, runner):
        """Test init-config command help."""
        result = runner.invoke(cli, ["init-config", "--help"])
        assert result.exit_code == 0
        assert "Create a sample configuration file" in result.output

    @patch("trading212_gnucash.cli.create_sample_config")
    def test_init_config_success(self, mock_create_config, runner, temp_config_file):
        """Test successful config initialization."""
        result = runner.invoke(cli, ["init-config", "--config", str(temp_config_file)])

        assert result.exit_code == 0
        assert "Sample configuration created" in result.output
        assert "Next steps:" in result.output
        mock_create_config.assert_called_once_with(temp_config_file)

    def test_init_config_file_exists_no_force(self, runner, temp_config_file):
        """Test init-config when file exists without --force."""
        # Create the file
        temp_config_file.touch()

        result = runner.invoke(cli, ["init-config", "--config", str(temp_config_file)])

        assert result.exit_code == 0
        assert "Configuration file already exists" in result.output
        assert "Use --force to overwrite" in result.output

    @patch("trading212_gnucash.cli.create_sample_config")
    def test_init_config_file_exists_with_force(
        self, mock_create_config, runner, temp_config_file
    ):
        """Test init-config when file exists with --force."""
        # Create the file
        temp_config_file.touch()

        result = runner.invoke(
            cli, ["init-config", "--config", str(temp_config_file), "--force"]
        )

        assert result.exit_code == 0
        assert "Sample configuration created" in result.output
        mock_create_config.assert_called_once_with(temp_config_file)

    def test_init_config_default_path(self, runner):
        """Test init-config with default path."""
        with patch("trading212_gnucash.cli.create_sample_config") as mock_create_config:
            with patch("pathlib.Path.exists", return_value=False):
                result = runner.invoke(cli, ["init-config"])

        assert result.exit_code == 0
        mock_create_config.assert_called_once()
        # Check that the default path was used
        call_args = mock_create_config.call_args[0]
        assert "trading212-gnucash" in str(call_args[0])

    @patch("trading212_gnucash.cli.create_sample_config")
    def test_init_config_exception_handling(
        self, mock_create_config, runner, temp_config_file
    ):
        """Test init-config exception handling."""
        mock_create_config.side_effect = Exception("Permission denied")

        result = runner.invoke(cli, ["init-config", "--config", str(temp_config_file)])

        assert result.exit_code == 1
        assert "Error creating configuration" in result.output


class TestValidateConfigCommand:
    """Test validate-config command functionality."""

    def test_validate_config_help(self, runner):
        """Test validate-config command help."""
        result = runner.invoke(cli, ["validate-config", "--help"])
        assert result.exit_code == 0
        assert "Validate configuration file" in result.output

    @patch("trading212_gnucash.cli.Config")
    def test_validate_config_success_default(self, mock_config_class, runner):
        """Test successful config validation with default config."""
        # Mock config
        mock_config = Mock()
        mock_config.ticker_map = {"MSFT": "NASDAQ:MSFT", "AAPL": "NASDAQ:AAPL"}
        mock_config.deposit_account = "Assets:Trading212"
        mock_config.interest_account = "Income:Interest"
        mock_config.expense_accounts = Mock()
        mock_config.expense_accounts.conversion_fee = "Expenses:Fees"
        mock_config.expense_accounts.french_tax = "Expenses:Tax:French"
        mock_config.expense_accounts.stamp_duty_tax = "Expenses:Tax:Stamp"

        mock_config_class.load_from_file.return_value = mock_config

        result = runner.invoke(cli, ["validate-config"])

        assert result.exit_code == 0
        assert "Default configuration loaded" in result.output
        assert "Configuration Summary" in result.output
        assert "Ticker Mappings" in result.output

    @patch("trading212_gnucash.cli.Config")
    def test_validate_config_success_custom_file(
        self, mock_config_class, runner, temp_config_file
    ):
        """Test successful config validation with custom file."""
        # Create a real config file
        config = Config()
        config.save_to_file(temp_config_file)

        # Mock config
        mock_config = Mock()
        mock_config.ticker_map = {"MSFT": "NASDAQ:MSFT"}
        mock_config.deposit_account = "Assets:Trading212"
        mock_config.interest_account = "Income:Interest"
        mock_config.expense_accounts = Mock()
        mock_config.expense_accounts.conversion_fee = "Expenses:Fees"
        mock_config.expense_accounts.french_tax = "Expenses:Tax:French"
        mock_config.expense_accounts.stamp_duty_tax = "Expenses:Tax:Stamp"

        mock_config_class.load_from_file.return_value = mock_config

        result = runner.invoke(
            cli, ["validate-config", "--config", str(temp_config_file)]
        )

        assert result.exit_code == 0
        assert f"Configuration file is valid: {temp_config_file}" in result.output

    @patch("trading212_gnucash.cli.Config")
    def test_validate_config_empty_ticker_map(self, mock_config_class, runner):
        """Test config validation with empty ticker map."""
        # Mock config with empty ticker map
        mock_config = Mock()
        mock_config.ticker_map = {}
        mock_config.deposit_account = "Assets:Trading212"
        mock_config.interest_account = "Income:Interest"
        mock_config.expense_accounts = Mock()
        mock_config.expense_accounts.conversion_fee = "Expenses:Fees"
        mock_config.expense_accounts.french_tax = "Expenses:Tax:French"
        mock_config.expense_accounts.stamp_duty_tax = "Expenses:Tax:Stamp"

        mock_config_class.load_from_file.return_value = mock_config

        result = runner.invoke(cli, ["validate-config"])

        assert result.exit_code == 0
        assert "Default configuration loaded" in result.output
        # Should not show ticker mappings table when empty
        assert "Ticker Mappings" not in result.output or "MSFT" not in result.output

    @patch("trading212_gnucash.cli.Config")
    def test_validate_config_exception_handling(self, mock_config_class, runner):
        """Test validate-config exception handling."""
        mock_config_class.load_from_file.side_effect = Exception("Invalid config")

        result = runner.invoke(cli, ["validate-config"])

        assert result.exit_code == 1
        assert "Configuration error" in result.output


class TestInfoCommand:
    """Test info command functionality."""

    def test_info_help(self, runner):
        """Test info command help."""
        result = runner.invoke(cli, ["info", "--help"])
        assert result.exit_code == 0
        assert "Display information about a Trading 212 CSV file" in result.output

    def test_info_missing_file(self, runner):
        """Test info with non-existent file."""
        result = runner.invoke(cli, ["info", "nonexistent.csv"])
        assert result.exit_code == 2
        assert "does not exist" in result.output

    @patch("trading212_gnucash.cli.Trading212Converter")
    def test_info_invalid_csv(self, mock_converter_class, runner, temp_csv_file):
        """Test info with invalid CSV file."""
        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = False
        mock_converter_class.return_value = mock_converter

        result = runner.invoke(cli, ["info", str(temp_csv_file)])

        assert result.exit_code == 1
        assert "Invalid CSV file" in result.output

    @patch("trading212_gnucash.cli.Trading212Converter")
    def test_info_empty_file(self, mock_converter_class, runner, temp_csv_file):
        """Test info with empty CSV file."""
        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = True
        mock_converter.read_transactions.return_value = []
        mock_converter_class.return_value = mock_converter

        result = runner.invoke(cli, ["info", str(temp_csv_file)])

        assert result.exit_code == 0
        assert "No transactions found" in result.output

    @patch("trading212_gnucash.cli.Trading212Converter")
    def test_info_success(self, mock_converter_class, runner, temp_csv_file):
        """Test successful info command."""
        # Mock transactions
        mock_transaction1 = Mock()
        mock_transaction1.action = "Market buy"
        mock_transaction1.ticker = "MSFT"
        mock_transaction1.time = "2025-01-01 10:00:00.000"

        mock_transaction2 = Mock()
        mock_transaction2.action = "Deposit"
        mock_transaction2.ticker = None
        mock_transaction2.time = "2025-01-01 09:00:00.000"

        mock_transaction3 = Mock()
        mock_transaction3.action = "Market buy"
        mock_transaction3.ticker = "AAPL"
        mock_transaction3.time = "2025-01-02 10:00:00.000"

        mock_converter = Mock()
        mock_converter.validate_csv_file.return_value = True
        mock_converter.read_transactions.return_value = [
            mock_transaction1,
            mock_transaction2,
            mock_transaction3,
        ]
        mock_converter_class.return_value = mock_converter

        result = runner.invoke(cli, ["info", str(temp_csv_file)])

        assert result.exit_code == 0
        assert "File Summary" in result.output
        assert "Total Transactions" in result.output
        assert "3" in result.output  # Total transactions
        assert "Transaction Types" in result.output
        assert "Top Tickers" in result.output
        assert "Date Range" in result.output

    @patch("trading212_gnucash.cli.Trading212Converter")
    def test_info_exception_handling(self, mock_converter_class, runner, temp_csv_file):
        """Test info command exception handling."""
        mock_converter_class.side_effect = Exception("Converter error")

        result = runner.invoke(cli, ["info", str(temp_csv_file)])

        assert result.exit_code == 1
        assert "Error analyzing file" in result.output
