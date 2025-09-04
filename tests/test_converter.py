"""Tests for the converter module.

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

import csv
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from trading212_gnucash.config import Config
from trading212_gnucash.converter import Trading212Converter
from trading212_gnucash.models import (
    ConversionResult,
    Trading212Transaction,
)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    config = Config()
    config.ticker_map = {
        "MSFT": "NASDAQ:MSFT",
        "AAPL": "NASDAQ:AAPL",
        "VOD": "VOD.L",
    }
    config.deposit_account = "Assets:Trading212:Cash"
    config.interest_account = "Income:Trading212:Interest"
    return config


@pytest.fixture
def converter(sample_config):
    """Converter instance with sample config."""
    return Trading212Converter(sample_config)


@pytest.fixture
def valid_csv_headers():
    """Valid CSV headers for Trading 212 export."""
    return [
        "Action",
        "Time",
        "ISIN",
        "Ticker",
        "Name",
        "Notes",
        "ID",
        "No. of shares",
        "Price / share",
        "Currency (Price / share)",
        "Exchange rate",
        "Currency (Result)",
        "Total",
        "Currency (Total)",
    ]


@pytest.fixture
def sample_csv_content():
    """Sample Trading 212 CSV content with various transaction types."""
    return """Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,Currency (Price / share),Exchange rate,Currency (Result),Total,Currency (Total)
Market buy,2025-01-01 10:00:00.000,US5949181045,MSFT,Microsoft Corporation,,12345,10.5,150.00,USD,0.8,GBP,-1260.00,GBP
Market sell,2025-01-02 11:00:00.000,US0378331005,AAPL,Apple Inc.,,12346,5.0,180.00,USD,0.85,GBP,765.00,GBP
Deposit,2025-01-01 09:00:00.000,,,,,54321,,,,,GBP,1000.00,GBP
Interest on cash,2025-01-15 12:00:00.000,,,,,54322,,,,,GBP,5.50,GBP
Market buy,2025-01-03 14:00:00.000,GB00BH4HKS39,VOD,Vodafone Group Plc,,12347,100.0,0.75,GBP,1.0,GBP,-75.00,GBP
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
def invalid_csv_content():
    """Invalid CSV content missing required headers."""
    return """Action,Time,ISIN
Market buy,2025-01-01 10:00:00.000,US5949181045
"""


@pytest.fixture
def temp_invalid_csv_file(invalid_csv_content):
    """Create a temporary invalid CSV file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(invalid_csv_content)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestTradingConverterInit:
    """Test Trading212Converter initialization."""

    def test_init_with_config(self, sample_config):
        """Test initialization with provided config."""
        converter = Trading212Converter(sample_config)
        assert converter.config == sample_config
        assert converter.logger is not None

    def test_init_without_config(self):
        """Test initialization without config uses defaults."""
        converter = Trading212Converter()
        assert converter.config is not None
        assert isinstance(converter.config, Config)
        assert converter.logger is not None

    def test_init_with_none_config(self):
        """Test initialization with None config uses defaults."""
        converter = Trading212Converter(None)
        assert converter.config is not None
        assert isinstance(converter.config, Config)


class TestValidateCSVFile:
    """Test CSV file validation functionality."""

    def test_validate_nonexistent_file(self, converter):
        """Test validation of non-existent file."""
        nonexistent_path = Path("nonexistent_file.csv")
        assert not converter.validate_csv_file(nonexistent_path)

    def test_validate_valid_csv_file(self, converter, temp_csv_file):
        """Test validation of valid CSV file."""
        assert converter.validate_csv_file(temp_csv_file)

    def test_validate_invalid_csv_file(self, converter, temp_invalid_csv_file):
        """Test validation of invalid CSV file."""
        assert not converter.validate_csv_file(temp_invalid_csv_file)

    def test_validate_csv_with_string_path(self, converter, temp_csv_file):
        """Test validation with string path instead of Path object."""
        assert converter.validate_csv_file(str(temp_csv_file))

    def test_validate_empty_csv_file(self, converter):
        """Test validation of empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            assert not converter.validate_csv_file(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_validate_csv_missing_trading_headers(self, converter):
        """Test validation of CSV missing trading-specific headers."""
        csv_content = """Action,Time,ISIN,Ticker,Name,Notes,ID,Total,Currency (Total)
Deposit,2025-01-01 09:00:00.000,,,,,54321,1000.00,GBP
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            # Should still be valid (trading headers are optional for non-trading transactions)
            assert converter.validate_csv_file(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_validate_csv_file_encoding_error(self, converter):
        """Test validation with file encoding issues."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
            # Write invalid UTF-8 bytes
            f.write(b"\xff\xfe\x00\x00")
            temp_path = Path(f.name)

        try:
            assert not converter.validate_csv_file(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestReadTransactions:
    """Test transaction reading functionality."""

    def test_read_transactions_valid_file(self, converter, temp_csv_file):
        """Test reading transactions from valid CSV file."""
        transactions = list(converter.read_transactions(temp_csv_file))
        assert len(transactions) == 5

        # Check first transaction (Market buy)
        first_transaction = transactions[0]
        assert first_transaction.action == "Market buy"
        assert first_transaction.ticker == "MSFT"
        assert first_transaction.num_shares == Decimal("10.5")
        assert first_transaction.price_per_share == Decimal("150.00")

        # Check deposit transaction
        deposit_transaction = transactions[2]
        assert deposit_transaction.action == "Deposit"
        assert deposit_transaction.ticker is None
        assert deposit_transaction.total == Decimal("1000.00")

    def test_read_transactions_with_string_path(self, converter, temp_csv_file):
        """Test reading transactions with string path."""
        transactions = list(converter.read_transactions(str(temp_csv_file)))
        assert len(transactions) == 5

    def test_read_transactions_empty_values(self, converter):
        """Test reading transactions with empty/None values."""
        csv_content = """Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,Currency (Price / share),Exchange rate,Currency (Result),Total,Currency (Total)
Deposit,2025-01-01 09:00:00.000,,,,,54321,,,,,GBP,1000.00,GBP
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            transactions = list(converter.read_transactions(temp_path))
            assert len(transactions) == 1
            transaction = transactions[0]
            assert transaction.action == "Deposit"
            assert transaction.ticker is None
            assert transaction.isin is None
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_read_transactions_invalid_row(self, converter):
        """Test reading transactions with invalid row data."""
        csv_content = """Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,Currency (Price / share),Exchange rate,Currency (Result),Total,Currency (Total)
Invalid Action,invalid-date,,,,,54321,invalid-shares,invalid-price,,,,invalid-total,GBP
Deposit,2025-01-01 09:00:00.000,,,,,54322,,,,,GBP,1000.00,GBP
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            transactions = list(converter.read_transactions(temp_path))
            # Should skip invalid row and return only valid one
            assert len(transactions) == 1
            assert transactions[0].action == "Deposit"
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestConvertTransaction:
    """Test individual transaction conversion."""

    def test_convert_deposit_transaction(self, converter):
        """Test converting a deposit transaction."""
        transaction = Trading212Transaction(
            action="Deposit",
            time="2025-01-01 09:00:00.000",
            id="54321",
            total=Decimal("1000.00"),
            total_currency="GBP",
        )

        result = converter.convert_transaction(transaction)
        assert isinstance(result, ConversionResult)
        assert len(result.splits) == 1
        assert len(result.errors) == 0

        split = result.splits[0]
        assert split.account == converter.config.deposit_account
        assert split.value == "1000.00"
        assert "Deposit from Trading 212" in split.description

    def test_convert_deposit_with_notes(self, converter):
        """Test converting a deposit transaction with notes."""
        transaction = Trading212Transaction(
            action="Deposit",
            time="2025-01-01 09:00:00.000",
            id="54321",
            total=Decimal("1000.00"),
            total_currency="GBP",
            notes="Bank transfer",
        )

        result = converter.convert_transaction(transaction)
        split = result.splits[0]
        assert "Bank transfer" in split.description

    def test_convert_interest_transaction(self, converter):
        """Test converting an interest transaction."""
        transaction = Trading212Transaction(
            action="Interest on cash",
            time="2025-01-15 12:00:00.000",
            id="54322",
            total=Decimal("5.50"),
            total_currency="GBP",
        )

        result = converter.convert_transaction(transaction)
        assert len(result.splits) == 1
        assert len(result.errors) == 0

        split = result.splits[0]
        assert split.account == converter.config.interest_account
        assert split.value == "5.50"
        assert "Interest on cash from Trading 212" in split.description

    def test_convert_market_buy_transaction(self, converter):
        """Test converting a market buy transaction."""
        transaction = Trading212Transaction(
            action="Market buy",
            time="2025-01-01 10:00:00.000",
            isin="US5949181045",
            ticker="MSFT",
            name="Microsoft Corporation",
            id="12345",
            num_shares=Decimal("10.5"),
            price_per_share=Decimal("150.00"),
            price_currency="USD",
            exchange_rate=Decimal("0.8"),
            result_currency="GBP",
            total=Decimal("-1260.00"),
            total_currency="GBP",
        )

        result = converter.convert_transaction(transaction)
        assert len(result.splits) == 1
        assert len(result.errors) == 0

        split = result.splits[0]
        assert split.transaction_commodity == "NASDAQ:MSFT"  # Mapped ticker
        assert split.amount == "10.500000"  # Buy action, positive amount
        assert "Purchase of 10.500000 shares" in split.memo

    def test_convert_market_sell_transaction(self, converter):
        """Test converting a market sell transaction."""
        transaction = Trading212Transaction(
            action="Market sell",
            time="2025-01-02 11:00:00.000",
            isin="US0378331005",
            ticker="AAPL",
            name="Apple Inc.",
            id="12346",
            num_shares=Decimal("5.0"),
            price_per_share=Decimal("180.00"),
            price_currency="USD",
            exchange_rate=Decimal("0.85"),
            result_currency="GBP",
            total=Decimal("765.00"),
            total_currency="GBP",
        )

        result = converter.convert_transaction(transaction)
        assert len(result.splits) == 1

        split = result.splits[0]
        assert split.transaction_commodity == "NASDAQ:AAPL"  # Mapped ticker
        assert split.amount == "-5.000000"  # Sell action, negative amount
        assert "Sale of 5.000000 shares" in split.memo

    def test_convert_trading_transaction_missing_data(self, converter):
        """Test converting trading transaction with missing required data."""
        transaction = Trading212Transaction(
            action="Market buy",
            time="2025-01-01 10:00:00.000",
            id="12345",
            ticker="MSFT",
            # Missing num_shares and price_per_share
            total=Decimal("-1260.00"),
            total_currency="GBP",
        )

        result = converter.convert_transaction(transaction)
        assert len(result.splits) == 0
        assert len(result.errors) == 1
        assert "Missing required trading data" in result.errors[0]

    def test_convert_unsupported_action(self, converter):
        """Test converting transaction with unsupported action type."""
        # Create a transaction with a supported action and then modify it
        transaction = Trading212Transaction(
            action="Deposit",
            time="2025-01-01 10:00:00.000",
            id="12345",
            total=Decimal("100.00"),
            total_currency="GBP",
        )
        # Manually change the action to something unsupported after validation
        transaction.action = "Unknown Action"

        result = converter.convert_transaction(transaction)
        assert len(result.splits) == 0
        assert len(result.errors) == 1
        assert "Unsupported action type" in result.errors[0]

    def test_convert_transaction_with_exception(self, converter):
        """Test conversion error handling when exception occurs."""
        # Create a mock transaction that will cause an exception
        transaction = Mock()
        transaction.action = "Deposit"
        # Make the transaction cause an exception when accessed
        transaction.time = property(lambda self: 1 / 0)

        result = converter.convert_transaction(transaction)
        assert len(result.splits) == 0
        assert len(result.errors) == 1
        assert "Error converting transaction" in result.errors[0]

    def test_convert_trading_with_unmapped_ticker(self, converter):
        """Test converting trading transaction with unmapped ticker."""
        transaction = Trading212Transaction(
            action="Market buy",
            time="2025-01-01 10:00:00.000",
            ticker="UNKNOWN",  # Not in ticker_map
            name="Unknown Corp",
            id="12345",
            num_shares=Decimal("10.0"),
            price_per_share=Decimal("100.00"),
            price_currency="GBP",
            total=Decimal("-1000.00"),
            total_currency="GBP",
        )

        result = converter.convert_transaction(transaction)
        assert len(result.warnings) == 1
        assert "No ticker mapping found for UNKNOWN" in result.warnings[0]

        split = result.splits[0]
        assert split.transaction_commodity == "UNKNOWN"  # Uses original ticker


class TestPrivateConversionMethods:
    """Test private conversion methods."""

    def test_convert_deposit_no_id(self, converter):
        """Test deposit conversion without ID."""
        transaction = Trading212Transaction(
            action="Deposit",
            time="2025-01-01 09:00:00.000",
            id="",  # Empty ID
            total=Decimal("1000.00"),
            total_currency="GBP",
        )

        result = converter._convert_deposit(transaction)
        split = result.splits[0]
        assert "Trading 212 deposit" in split.memo
        assert "ID:" not in split.memo

    def test_convert_interest_no_id(self, converter):
        """Test interest conversion without ID."""
        transaction = Trading212Transaction(
            action="Interest on cash",
            time="2025-01-15 12:00:00.000",
            id="",  # Empty ID
            total=Decimal("5.50"),
            total_currency="GBP",
        )

        result = converter._convert_interest(transaction)
        split = result.splits[0]
        assert "Trading 212 interest payment" in split.memo
        assert "ID:" not in split.memo

    def test_calculate_gbp_price_with_exchange_rate(self, converter):
        """Test GBP price calculation using exchange rate."""
        transaction = Trading212Transaction(
            action="Market buy",
            time="2025-01-01 10:00:00.000",
            id="12345",
            ticker="MSFT",
            num_shares=Decimal("10.0"),
            price_per_share=Decimal("150.00"),
            price_currency="USD",
            exchange_rate=Decimal("0.8"),
            total=Decimal("-1200.00"),
            total_currency="GBP",
        )

        gbp_price = converter._calculate_gbp_price(transaction)
        assert gbp_price == Decimal("187.5")  # 150 / 0.8

    def test_calculate_gbp_price_from_total(self, converter):
        """Test GBP price calculation from total amount."""
        transaction = Trading212Transaction(
            action="Market buy",
            time="2025-01-01 10:00:00.000",
            id="12345",
            ticker="MSFT",
            num_shares=Decimal("10.0"),
            price_per_share=Decimal("150.00"),
            price_currency="GBP",
            total=Decimal("-1500.00"),
            total_currency="GBP",
        )

        gbp_price = converter._calculate_gbp_price(transaction)
        assert gbp_price == Decimal("150.0")  # 1500 / 10

    def test_calculate_gbp_price_already_gbp(self, converter):
        """Test GBP price calculation when already in GBP."""
        transaction = Trading212Transaction(
            action="Market buy",
            time="2025-01-01 10:00:00.000",
            id="12345",
            ticker="VOD",
            num_shares=Decimal("100.0"),
            price_per_share=Decimal("0.75"),
            price_currency="GBP",
            total=Decimal("-75.00"),
            total_currency="GBP",
        )

        gbp_price = converter._calculate_gbp_price(transaction)
        assert gbp_price == Decimal("0.75")

    def test_create_share_split_buy(self, converter):
        """Test creating share split for buy action."""
        transaction = Trading212Transaction(
            action="Market buy",
            time="2025-01-01 10:00:00.000",
            ticker="MSFT",
            name="Microsoft Corporation",
            id="12345",
            num_shares=Decimal("10.5"),
            price_per_share=Decimal("150.00"),
            total=Decimal("-1575.00"),
            total_currency="GBP",
        )

        split = converter._create_share_split(
            transaction, "Test description", "NASDAQ:MSFT", Decimal("1575.00")
        )

        assert split.amount == "10.500000"
        assert "Purchase of 10.500000 shares" in split.memo
        assert split.transaction_commodity == "NASDAQ:MSFT"

    def test_create_share_split_sell(self, converter):
        """Test creating share split for sell action."""
        transaction = Trading212Transaction(
            action="Market sell",
            time="2025-01-02 11:00:00.000",
            ticker="AAPL",
            name="Apple Inc.",
            id="12346",
            num_shares=Decimal("5.0"),
            price_per_share=Decimal("180.00"),
            total=Decimal("900.00"),
            total_currency="GBP",
        )

        split = converter._create_share_split(
            transaction, "Test description", "NASDAQ:AAPL", Decimal("900.00")
        )

        assert split.amount == "-5.000000"
        assert "Sale of 5.000000 shares" in split.memo
        assert split.transaction_commodity == "NASDAQ:AAPL"


class TestConvertFile:
    """Test full file conversion functionality."""

    def test_convert_file_success(self, converter, temp_csv_file):
        """Test successful file conversion."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as output_file:
            output_path = Path(output_file.name)

        try:
            result = converter.convert_file(temp_csv_file, output_path)
            assert result is True
            assert output_path.exists()

            # Check output file content
            with open(output_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Should have splits for all transactions
            assert len(rows) > 0

            # Check headers
            expected_headers = [
                "Date",
                "Number",
                "Description",
                "Memo",
                "Account",
                "Transaction Commodity",
                "Amount",
                "Value",
            ]
            assert reader.fieldnames == expected_headers

        finally:
            if output_path.exists():
                output_path.unlink()

    def test_convert_file_invalid_input(self, converter, temp_invalid_csv_file):
        """Test file conversion with invalid input file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as output_file:
            output_path = Path(output_file.name)

        try:
            result = converter.convert_file(temp_invalid_csv_file, output_path)
            assert result is False
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_convert_file_with_string_paths(self, converter, temp_csv_file):
        """Test file conversion with string paths."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as output_file:
            output_path = Path(output_file.name)

        try:
            result = converter.convert_file(str(temp_csv_file), str(output_path))
            assert result is True
            assert output_path.exists()
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_convert_file_write_error(self, converter, temp_csv_file):
        """Test file conversion with write error."""
        # Try to write to a directory that doesn't exist
        invalid_output = Path("/nonexistent/directory/output.csv")

        result = converter.convert_file(temp_csv_file, invalid_output)
        assert result is False

    def test_convert_file_with_errors_and_warnings(self, converter):
        """Test file conversion with transactions that generate errors and warnings."""
        csv_content = """Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,Currency (Price / share),Exchange rate,Currency (Result),Total,Currency (Total)
Market buy,2025-01-01 10:00:00.000,US5949181045,MSFT,Microsoft Corporation,,12345,10.5,150.00,USD,0.8,GBP,-1260.00,GBP
Market buy,2025-01-02 11:00:00.000,,,,,12346,,,,,,,-1000.00,GBP
Unsupported Action,2025-01-03 12:00:00.000,,,,,12347,,,,,GBP,100.00,GBP
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as input_file:
            input_file.write(csv_content)
            input_path = Path(input_file.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as output_file:
            output_path = Path(output_file.name)

        try:
            result = converter.convert_file(input_path, output_path)
            assert result is True  # Should still succeed despite errors

            # Check that valid transactions were processed
            with open(output_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Should have at least one valid transaction
            assert len(rows) >= 1

        finally:
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()


class TestConverterIntegration:
    """Integration tests for the converter."""

    def test_end_to_end_conversion(self, sample_config):
        """Test complete end-to-end conversion process."""
        converter = Trading212Converter(sample_config)

        # Create test data with various transaction types
        csv_content = """Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,Currency (Price / share),Exchange rate,Currency (Result),Total,Currency (Total)
Deposit,2025-01-01 08:00:00.000,,,,,D001,,,,,GBP,2000.00,GBP
Market buy,2025-01-01 10:00:00.000,US5949181045,MSFT,Microsoft Corporation,,B001,10.0,150.00,USD,0.8,GBP,-1500.00,GBP
Interest on cash,2025-01-15 12:00:00.000,,,,,I001,,,,,GBP,12.50,GBP
Market sell,2025-01-20 14:00:00.000,US5949181045,MSFT,Microsoft Corporation,,S001,5.0,160.00,USD,0.75,GBP,600.00,GBP
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as input_file:
            input_file.write(csv_content)
            input_path = Path(input_file.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as output_file:
            output_path = Path(output_file.name)

        try:
            # Validate and convert
            assert converter.validate_csv_file(input_path)
            assert converter.convert_file(input_path, output_path)

            # Verify output
            with open(output_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Should have 4 splits (one for each transaction)
            assert len(rows) == 4

            # Verify specific transactions
            deposit_split = rows[0]
            assert deposit_split["Account"] == sample_config.deposit_account
            assert deposit_split["Value"] == "2000.00"

            buy_split = rows[1]
            assert buy_split["Transaction Commodity"] == "NASDAQ:MSFT"
            assert buy_split["Amount"] == "10.000000"

            interest_split = rows[2]
            assert interest_split["Account"] == sample_config.interest_account
            assert interest_split["Value"] == "12.50"

            sell_split = rows[3]
            assert sell_split["Transaction Commodity"] == "NASDAQ:MSFT"
            assert sell_split["Amount"] == "-5.000000"

        finally:
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()
