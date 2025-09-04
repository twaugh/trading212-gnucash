"""Tests for the config module.

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

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from trading212_gnucash.config import Config, ExpenseAccounts, create_sample_config


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


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "ticker_map": {
            "MSFT": "NASDAQ:MSFT",
            "AAPL": "NASDAQ:AAPL",
            "TEST": "TEST.L",
        },
        "deposit_account": "Assets:Test:Deposits",
        "interest_account": "Income:Test:Interest",
        "expense_accounts": {
            "conversion_fee": "Expenses:Test:Conversion",
            "french_tax": "Expenses:Test:French",
            "stamp_duty_tax": "Expenses:Test:Stamp",
        },
    }


@pytest.fixture
def sample_yaml_config(temp_config_file, sample_config_data):
    """Create a sample YAML config file."""
    with open(temp_config_file, "w", encoding="utf-8") as f:
        yaml.dump(sample_config_data, f)
    return temp_config_file


class TestExpenseAccounts:
    """Test ExpenseAccounts model."""

    def test_expense_accounts_defaults(self):
        """Test ExpenseAccounts with default values."""
        accounts = ExpenseAccounts()
        assert accounts.conversion_fee == "Expenses:Currency Conversion Fees"
        assert accounts.french_tax == "Expenses:French Transaction Tax"
        assert accounts.stamp_duty_tax == "Expenses:Stamp Duty Reserve Tax"

    def test_expense_accounts_custom_values(self):
        """Test ExpenseAccounts with custom values."""
        accounts = ExpenseAccounts(
            conversion_fee="Custom:Conversion",
            french_tax="Custom:French",
            stamp_duty_tax="Custom:Stamp",
        )
        assert accounts.conversion_fee == "Custom:Conversion"
        assert accounts.french_tax == "Custom:French"
        assert accounts.stamp_duty_tax == "Custom:Stamp"

    def test_expense_accounts_partial_values(self):
        """Test ExpenseAccounts with partial custom values."""
        accounts = ExpenseAccounts(conversion_fee="Custom:Conversion")
        assert accounts.conversion_fee == "Custom:Conversion"
        assert accounts.french_tax == "Expenses:French Transaction Tax"  # Default
        assert accounts.stamp_duty_tax == "Expenses:Stamp Duty Reserve Tax"  # Default


class TestConfigDefaults:
    """Test Config class initialization and defaults."""

    def test_config_defaults(self):
        """Test Config with default values."""
        config = Config()

        # Check default ticker map
        assert "ACME" in config.ticker_map
        assert "VOD" in config.ticker_map
        assert "MSFT" in config.ticker_map
        assert "AAPL" in config.ticker_map
        assert "GOOGL" in config.ticker_map
        assert config.ticker_map["ACME"] == "ACME.L"
        assert config.ticker_map["MSFT"] == "MSFT"

        # Check default accounts
        assert config.deposit_account == "Assets:Trading 212 Deposits"
        assert config.interest_account == "Income:Trading 212 Interest"

        # Check default expense accounts
        assert isinstance(config.expense_accounts, ExpenseAccounts)
        assert (
            config.expense_accounts.conversion_fee
            == "Expenses:Currency Conversion Fees"
        )

    def test_config_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            ticker_map={"TEST": "TEST.L"},
            deposit_account="Custom:Deposits",
            interest_account="Custom:Interest",
        )

        assert config.ticker_map == {"TEST": "TEST.L"}
        assert config.deposit_account == "Custom:Deposits"
        assert config.interest_account == "Custom:Interest"

    def test_config_with_custom_expense_accounts(self):
        """Test Config with custom expense accounts."""
        expense_accounts = ExpenseAccounts(conversion_fee="Custom:Fees")
        config = Config(expense_accounts=expense_accounts)

        assert config.expense_accounts.conversion_fee == "Custom:Fees"
        assert config.expense_accounts.french_tax == "Expenses:French Transaction Tax"


class TestConfigLoadFromFile:
    """Test Config.load_from_file method."""

    def test_load_from_file_with_valid_config(
        self, sample_yaml_config, sample_config_data
    ):
        """Test loading valid config file."""
        config = Config.load_from_file(sample_yaml_config)

        assert config.ticker_map == sample_config_data["ticker_map"]
        assert config.deposit_account == sample_config_data["deposit_account"]
        assert config.interest_account == sample_config_data["interest_account"]
        assert config.expense_accounts.conversion_fee == "Expenses:Test:Conversion"

    def test_load_from_file_nonexistent(self):
        """Test loading from non-existent file returns defaults."""
        config = Config.load_from_file("nonexistent_config.yaml")

        # Should return default config
        assert "MSFT" in config.ticker_map
        assert config.deposit_account == "Assets:Trading 212 Deposits"

    def test_load_from_file_with_string_path(self, sample_yaml_config):
        """Test loading with string path."""
        config = Config.load_from_file(str(sample_yaml_config))
        assert config.ticker_map["MSFT"] == "NASDAQ:MSFT"

    def test_load_from_file_empty_file(self, temp_config_file):
        """Test loading from empty file."""
        # Create empty file
        temp_config_file.touch()

        config = Config.load_from_file(temp_config_file)

        # Should return default config
        assert "MSFT" in config.ticker_map
        assert config.deposit_account == "Assets:Trading 212 Deposits"

    def test_load_from_file_none_content(self, temp_config_file):
        """Test loading file with None content."""
        with open(temp_config_file, "w", encoding="utf-8") as f:
            f.write("# Just comments\n")

        config = Config.load_from_file(temp_config_file)

        # Should return default config
        assert "MSFT" in config.ticker_map

    def test_load_from_file_invalid_yaml(self, temp_config_file):
        """Test loading file with invalid YAML."""
        with open(temp_config_file, "w", encoding="utf-8") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ValueError, match="Error loading config file"):
            Config.load_from_file(temp_config_file)

    def test_load_from_file_invalid_config_data(self, temp_config_file):
        """Test loading file with invalid config data."""
        invalid_data = {"ticker_map": "not_a_dict"}  # Should be dict
        with open(temp_config_file, "w", encoding="utf-8") as f:
            yaml.dump(invalid_data, f)

        with pytest.raises(ValueError, match="Error loading config file"):
            Config.load_from_file(temp_config_file)

    def test_load_from_file_none_path_no_defaults(self):
        """Test loading with None path when no default files exist."""
        with patch("pathlib.Path.exists", return_value=False):
            config = Config.load_from_file(None)

            # Should return default config
            assert "MSFT" in config.ticker_map

    def test_load_from_file_none_path_with_defaults(self, sample_yaml_config):
        """Test loading with None path when default files exist."""
        # Create a mock path that exists and points to our test file
        mock_path = Path("~/.config/trading212-gnucash/config.yaml").expanduser()

        # Copy our test file to the expected location
        mock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sample_yaml_config, encoding="utf-8") as src:
            with open(mock_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())

        try:
            config = Config.load_from_file(None)
            assert config.ticker_map["MSFT"] == "NASDAQ:MSFT"
        finally:
            # Cleanup
            if mock_path.exists():
                mock_path.unlink()
            if mock_path.parent.exists() and not any(mock_path.parent.iterdir()):
                mock_path.parent.rmdir()

    def test_load_from_file_searches_default_paths(self):
        """Test that load_from_file searches default paths in order."""
        # Create a temporary config file in current directory (third default path)
        temp_config = Path("trading212_config.yaml")
        config_data = {"ticker_map": {"TEST": "TEST.L"}}

        with open(temp_config, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        try:
            config = Config.load_from_file(None)
            # Should find our config file and load it
            assert config.ticker_map["TEST"] == "TEST.L"
        finally:
            # Cleanup
            if temp_config.exists():
                temp_config.unlink()


class TestConfigLoadFromEnv:
    """Test Config.load_from_env method."""

    def test_load_from_env_empty(self):
        """Test loading from environment with no relevant variables."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.load_from_env()

            # Should return default config
            assert "MSFT" in config.ticker_map
            assert config.deposit_account == "Assets:Trading 212 Deposits"

    def test_load_from_env_ticker_mappings(self):
        """Test loading ticker mappings from environment."""
        env_vars = {
            "TRADING212_TICKER_MSFT": "NASDAQ:MSFT",
            "TRADING212_TICKER_AAPL": "NASDAQ:AAPL",
            "TRADING212_TICKER_TEST": "TEST.L",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.load_from_env()

            assert config.ticker_map["MSFT"] == "NASDAQ:MSFT"
            assert config.ticker_map["AAPL"] == "NASDAQ:AAPL"
            assert config.ticker_map["TEST"] == "TEST.L"

    def test_load_from_env_account_settings(self):
        """Test loading account settings from environment."""
        env_vars = {
            "TRADING212_DEPOSIT_ACCOUNT": "Assets:Env:Deposits",
            "TRADING212_INTEREST_ACCOUNT": "Income:Env:Interest",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.load_from_env()

            assert config.deposit_account == "Assets:Env:Deposits"
            assert config.interest_account == "Income:Env:Interest"

    def test_load_from_env_expense_accounts(self):
        """Test loading expense accounts from environment."""
        env_vars = {
            "TRADING212_CONVERSION_FEE_ACCOUNT": "Expenses:Env:Conversion",
            "TRADING212_FRENCH_TAX_ACCOUNT": "Expenses:Env:French",
            "TRADING212_STAMP_DUTY_ACCOUNT": "Expenses:Env:Stamp",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.load_from_env()

            assert config.expense_accounts.conversion_fee == "Expenses:Env:Conversion"
            assert config.expense_accounts.french_tax == "Expenses:Env:French"
            assert config.expense_accounts.stamp_duty_tax == "Expenses:Env:Stamp"

    def test_load_from_env_partial_expense_accounts(self):
        """Test loading partial expense accounts from environment."""
        env_vars = {
            "TRADING212_CONVERSION_FEE_ACCOUNT": "Expenses:Env:Conversion",
            # Only one expense account set
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.load_from_env()

            assert config.expense_accounts.conversion_fee == "Expenses:Env:Conversion"
            # Others should use defaults
            assert (
                config.expense_accounts.french_tax == "Expenses:French Transaction Tax"
            )
            assert (
                config.expense_accounts.stamp_duty_tax
                == "Expenses:Stamp Duty Reserve Tax"
            )

    def test_load_from_env_mixed_settings(self):
        """Test loading mixed settings from environment."""
        env_vars = {
            "TRADING212_TICKER_MSFT": "NASDAQ:MSFT",
            "TRADING212_DEPOSIT_ACCOUNT": "Assets:Env:Deposits",
            "TRADING212_CONVERSION_FEE_ACCOUNT": "Expenses:Env:Conversion",
            "OTHER_VAR": "should_be_ignored",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.load_from_env()

            assert config.ticker_map["MSFT"] == "NASDAQ:MSFT"
            assert config.deposit_account == "Assets:Env:Deposits"
            assert config.expense_accounts.conversion_fee == "Expenses:Env:Conversion"


class TestConfigSaveToFile:
    """Test Config.save_to_file method."""

    def test_save_to_file_basic(self, temp_config_file):
        """Test basic save to file functionality."""
        config = Config(
            ticker_map={"TEST": "TEST.L"},
            deposit_account="Assets:Test:Deposits",
        )

        config.save_to_file(temp_config_file)

        assert temp_config_file.exists()

        # Load and verify content
        with open(temp_config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["ticker_map"]["TEST"] == "TEST.L"
        assert data["deposit_account"] == "Assets:Test:Deposits"

    def test_save_to_file_creates_directory(self):
        """Test that save_to_file creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "subdir" / "config.yaml"

            config = Config()
            config.save_to_file(config_path)

            assert config_path.exists()
            assert config_path.parent.exists()

    def test_save_to_file_with_string_path(self, temp_config_file):
        """Test save to file with string path."""
        config = Config(ticker_map={"TEST": "TEST.L"})

        config.save_to_file(str(temp_config_file))

        assert temp_config_file.exists()

    def test_save_to_file_complex_config(self, temp_config_file):
        """Test saving complex configuration."""
        expense_accounts = ExpenseAccounts(
            conversion_fee="Custom:Conversion",
            french_tax="Custom:French",
            stamp_duty_tax="Custom:Stamp",
        )

        config = Config(
            ticker_map={"MSFT": "NASDAQ:MSFT", "AAPL": "NASDAQ:AAPL"},
            deposit_account="Assets:Custom:Deposits",
            interest_account="Income:Custom:Interest",
            expense_accounts=expense_accounts,
        )

        config.save_to_file(temp_config_file)

        # Load and verify
        loaded_config = Config.load_from_file(temp_config_file)

        assert loaded_config.ticker_map == config.ticker_map
        assert loaded_config.deposit_account == config.deposit_account
        assert loaded_config.interest_account == config.interest_account
        assert loaded_config.expense_accounts.conversion_fee == "Custom:Conversion"


class TestConfigHelperMethods:
    """Test Config helper methods."""

    def test_get_gnucash_ticker_mapped(self):
        """Test get_gnucash_ticker with mapped ticker."""
        config = Config(ticker_map={"MSFT": "NASDAQ:MSFT"})

        result = config.get_gnucash_ticker("MSFT")
        assert result == "NASDAQ:MSFT"

    def test_get_gnucash_ticker_unmapped(self):
        """Test get_gnucash_ticker with unmapped ticker."""
        config = Config(ticker_map={"MSFT": "NASDAQ:MSFT"})

        result = config.get_gnucash_ticker("UNKNOWN")
        assert result == "UNKNOWN"  # Fallback to original

    def test_get_gnucash_ticker_empty_map(self):
        """Test get_gnucash_ticker with empty ticker map."""
        config = Config(ticker_map={})

        result = config.get_gnucash_ticker("MSFT")
        assert result == "MSFT"

    def test_get_yahoo_ticker_deprecated(self):
        """Test deprecated get_yahoo_ticker method."""
        config = Config(ticker_map={"MSFT": "NASDAQ:MSFT"})

        result = config.get_yahoo_ticker("MSFT")
        assert result == "NASDAQ:MSFT"  # Should work the same as get_gnucash_ticker

    def test_get_tax_account_french(self):
        """Test get_tax_account for French tax."""
        config = Config()

        result = config.get_tax_account("french")
        assert result == config.expense_accounts.french_tax

    def test_get_tax_account_stamp_duty(self):
        """Test get_tax_account for stamp duty."""
        config = Config()

        result = config.get_tax_account("stamp_duty")
        assert result == config.expense_accounts.stamp_duty_tax

    def test_get_tax_account_unknown(self):
        """Test get_tax_account for unknown tax type."""
        config = Config()

        result = config.get_tax_account("unknown_tax")
        assert result == config.expense_accounts.french_tax  # Default fallback

    def test_get_tax_account_with_custom_accounts(self):
        """Test get_tax_account with custom expense accounts."""
        expense_accounts = ExpenseAccounts(
            french_tax="Custom:French",
            stamp_duty_tax="Custom:Stamp",
        )
        config = Config(expense_accounts=expense_accounts)

        assert config.get_tax_account("french") == "Custom:French"
        assert config.get_tax_account("stamp_duty") == "Custom:Stamp"
        assert config.get_tax_account("unknown") == "Custom:French"


class TestCreateSampleConfig:
    """Test create_sample_config function."""

    def test_create_sample_config_basic(self, temp_config_file):
        """Test basic sample config creation."""
        create_sample_config(temp_config_file)

        assert temp_config_file.exists()

        # Check that it's a valid config
        config = Config.load_from_file(temp_config_file)

        # Should have default values plus examples
        assert "MSFT" in config.ticker_map  # Default
        assert "TSLA" in config.ticker_map  # Added example
        assert "FAKE" in config.ticker_map  # Added example
        assert config.ticker_map["FAKE"] == "FAKE.L"

    def test_create_sample_config_with_string_path(self, temp_config_file):
        """Test sample config creation with string path."""
        create_sample_config(str(temp_config_file))

        assert temp_config_file.exists()

    def test_create_sample_config_creates_directory(self):
        """Test that create_sample_config creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "subdir" / "config.yaml"

            create_sample_config(config_path)

            assert config_path.exists()
            assert config_path.parent.exists()

    def test_create_sample_config_has_comments(self, temp_config_file):
        """Test that sample config includes helpful comments."""
        create_sample_config(temp_config_file)

        with open(temp_config_file, encoding="utf-8") as f:
            content = f.read()

        assert "Trading 212 to GnuCash" in content
        assert "ticker_map:" in content
        assert "Configuration Notes:" in content
        assert "expense_accounts:" in content

    def test_create_sample_config_valid_yaml(self, temp_config_file):
        """Test that created sample config is valid YAML."""
        create_sample_config(temp_config_file)

        # Should be able to load without errors
        config = Config.load_from_file(temp_config_file)

        assert isinstance(config.ticker_map, dict)
        assert len(config.ticker_map) > 5  # Should have defaults plus examples

    def test_create_sample_config_example_tickers(self, temp_config_file):
        """Test that sample config includes example tickers."""
        create_sample_config(temp_config_file)

        config = Config.load_from_file(temp_config_file)

        # Check for example tickers that should be added
        example_tickers = ["TSLA", "AMZN", "NFLX", "META", "NVDA", "FAKE"]
        for ticker in example_tickers:
            assert ticker in config.ticker_map

        # Check specific mappings
        assert config.ticker_map["TSLA"] == "TSLA"
        assert config.ticker_map["FAKE"] == "FAKE.L"


class TestConfigIntegration:
    """Integration tests for Config functionality."""

    def test_round_trip_save_load(self, temp_config_file):
        """Test saving and loading config maintains data integrity."""
        original_config = Config(
            ticker_map={"MSFT": "NASDAQ:MSFT", "TEST": "TEST.L"},
            deposit_account="Assets:Test:Deposits",
            interest_account="Income:Test:Interest",
            expense_accounts=ExpenseAccounts(
                conversion_fee="Expenses:Test:Conversion",
                french_tax="Expenses:Test:French",
                stamp_duty_tax="Expenses:Test:Stamp",
            ),
        )

        # Save and load
        original_config.save_to_file(temp_config_file)
        loaded_config = Config.load_from_file(temp_config_file)

        # Verify all data is preserved
        assert loaded_config.ticker_map == original_config.ticker_map
        assert loaded_config.deposit_account == original_config.deposit_account
        assert loaded_config.interest_account == original_config.interest_account
        assert (
            loaded_config.expense_accounts.conversion_fee
            == original_config.expense_accounts.conversion_fee
        )
        assert (
            loaded_config.expense_accounts.french_tax
            == original_config.expense_accounts.french_tax
        )
        assert (
            loaded_config.expense_accounts.stamp_duty_tax
            == original_config.expense_accounts.stamp_duty_tax
        )

    def test_env_vs_file_precedence(self, sample_yaml_config):
        """Test that environment variables work independently of file config."""
        # Load from file
        file_config = Config.load_from_file(sample_yaml_config)

        # Load from env
        env_vars = {
            "TRADING212_TICKER_MSFT": "ENV:MSFT",
            "TRADING212_DEPOSIT_ACCOUNT": "Assets:Env:Deposits",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            env_config = Config.load_from_env()

        # They should be different
        assert file_config.ticker_map["MSFT"] != env_config.ticker_map["MSFT"]
        assert file_config.deposit_account != env_config.deposit_account

    def test_config_methods_with_defaults(self):
        """Test that all config methods work with default config."""
        config = Config()

        # Test all helper methods
        assert config.get_gnucash_ticker("MSFT") == "MSFT"
        assert config.get_gnucash_ticker("UNKNOWN") == "UNKNOWN"
        assert config.get_yahoo_ticker("MSFT") == "MSFT"
        assert config.get_tax_account("french") == config.expense_accounts.french_tax
        assert (
            config.get_tax_account("stamp_duty")
            == config.expense_accounts.stamp_duty_tax
        )
        assert config.get_tax_account("unknown") == config.expense_accounts.french_tax
