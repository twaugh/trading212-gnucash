"""Basic tests to verify package structure and imports.

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

import pytest
from decimal import Decimal

from trading212_gnucash import Trading212Converter, Config
from trading212_gnucash.models import Trading212Transaction, GnuCashSplit


def test_imports():
    """Test that all modules can be imported."""
    assert Trading212Converter is not None
    assert Config is not None
    assert Trading212Transaction is not None
    assert GnuCashSplit is not None


def test_config_creation():
    """Test config creation with defaults."""
    config = Config()
    assert config.deposit_account == "Assets:Trading 212 Deposits"
    assert config.interest_account == "Income:Trading 212 Interest"
    assert "MSFT" in config.ticker_map
    assert "ACME" in config.ticker_map


def test_converter_creation():
    """Test converter creation."""
    converter = Trading212Converter()
    assert converter.config is not None
    
    config = Config()
    converter_with_config = Trading212Converter(config)
    assert converter_with_config.config == config


def test_transaction_model():
    """Test Trading212Transaction model validation."""
    # Valid transaction
    transaction_data = {
        "Action": "Market buy",
        "Time": "2025-01-01 10:00:00.000",
        "ISIN": "US5949181045",
        "Ticker": "MSFT",
        "Name": "Microsoft Corporation",
        "Notes": "",
        "ID": "12345",
        "No. of shares": "10.5",
        "Price / share": "150.00",
        "Currency (Price / share)": "USD",
        "Exchange rate": "0.8",
        "Currency (Result)": "GBP",
        "Total": "1968.75",
        "Currency (Total)": "GBP"
    }
    
    transaction = Trading212Transaction(**transaction_data)
    assert transaction.action == "Market buy"
    assert transaction.ticker == "MSFT"
    assert transaction.name == "Microsoft Corporation"
    assert transaction.num_shares == Decimal("10.5")
    assert transaction.is_trading_action() is True
    assert transaction.is_buy_action() is True
    assert transaction.is_sell_action() is False
    
    # Test that optional fields can be None
    minimal_data = {
        "Action": "Deposit",
        "Time": "2025-01-01 10:00:00.000", 
        "ID": "12345",
        "Total": "100.00",
        "Currency (Total)": "GBP"
    }
    deposit_transaction = Trading212Transaction(**minimal_data)
    assert deposit_transaction.action == "Deposit"
    assert deposit_transaction.ticker is None
    assert deposit_transaction.name is None
    assert deposit_transaction.isin is None


def test_gnucash_split_model():
    """Test GnuCashSplit model."""
    split = GnuCashSplit(
        date="2025-01-01 10:00:00.000",
        number="12345",
        description="Test transaction",
        memo="Test memo",
        account="Assets:Stocks:MSFT",
        transaction_commodity="MSFT",
        amount="10.5",
        value="1575.00"
    )
    
    assert split.date == "2025-01-01 10:00:00.000"
    assert split.account == "Assets:Stocks:MSFT"
    
    # Test dictionary conversion
    split_dict = split.to_dict()
    assert split_dict["Date"] == "2025-01-01 10:00:00.000"
    assert split_dict["Account"] == "Assets:Stocks:MSFT"
    assert split_dict["Transaction Commodity"] == "MSFT"
