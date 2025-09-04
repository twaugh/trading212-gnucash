"""Core converter functionality for Trading 212 to GnuCash conversion.

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
import logging
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Optional, Union

from .config import Config
from .models import ConversionResult, GnuCashSplit, Trading212Transaction


class Trading212Converter:
    """Main converter class for Trading 212 CSV files."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the converter with configuration."""
        self.logger = logging.getLogger(__name__)
        self.config = config or Config()

    def validate_csv_file(self, input_file: Union[str, Path]) -> bool:
        """Validate that the input CSV file has the expected format."""
        input_file = Path(input_file)

        if not input_file.exists():
            self.logger.error(f"Input file does not exist: {input_file}")
            return False

        try:
            with open(input_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                # Core required headers
                core_required_headers = [
                    "Action",
                    "Time",
                    "ISIN",
                    "Ticker",
                    "Name",
                    "Notes",
                    "ID",
                    "Total",
                    "Currency (Total)",
                ]

                # Check for core headers
                missing_core = [h for h in core_required_headers if h not in headers]
                if missing_core:
                    self.logger.error(f"Missing required headers: {missing_core}")
                    return False

                self.logger.info(f"CSV contains {len(headers)} columns")
                self.logger.debug(f"Headers: {', '.join(headers)}")

                # Check for trading-specific headers
                trading_headers = [
                    "No. of shares",
                    "Price / share",
                    "Currency (Price / share)",
                    "Exchange rate",
                    "Currency (Result)",
                ]

                missing_trading = [h for h in trading_headers if h not in headers]
                if missing_trading:
                    self.logger.warning(
                        f"Missing trading headers: {missing_trading}. "
                        "This may cause issues with buy/sell transactions."
                    )

        except Exception as e:
            self.logger.error(f"Error reading input file: {e}")
            return False

        return True

    def read_transactions(
        self, input_file: Union[str, Path]
    ) -> Iterator[Trading212Transaction]:
        """Read and parse Trading 212 transactions from CSV file."""
        input_file = Path(input_file)

        with open(input_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, 1):
                try:
                    # Clean up the row data - handle None values and empty strings
                    cleaned_row = {}
                    for key, value in row.items():
                        if value is None or value == "":
                            cleaned_row[key] = None
                        else:
                            cleaned_row[key] = (
                                value.strip() if isinstance(value, str) else value
                            )

                    transaction = Trading212Transaction(**cleaned_row)
                    yield transaction

                except Exception as e:
                    self.logger.error(f"Error parsing row {row_num}: {e}")
                    self.logger.debug(f"Row data: {row}")
                    continue

    def convert_transaction(
        self, transaction: Trading212Transaction
    ) -> ConversionResult:
        """Convert a single Trading212 transaction to GnuCash splits."""
        try:
            if transaction.action == "Deposit":
                return self._convert_deposit(transaction)
            elif transaction.action == "Interest on cash":
                return self._convert_interest(transaction)
            elif transaction.is_trading_action():
                return self._convert_trading_transaction(transaction)
            else:
                return ConversionResult(
                    splits=[], errors=[f"Unsupported action type: {transaction.action}"]
                )

        except Exception as e:
            return ConversionResult(
                splits=[], errors=[f"Error converting transaction: {e}"]
            )

    def _convert_deposit(self, transaction: Trading212Transaction) -> ConversionResult:
        """Convert a deposit transaction."""
        description = "Deposit from Trading 212"
        if transaction.notes:
            description += f" - {transaction.notes}"

        memo = (
            f"Trading 212 deposit - ID: {transaction.id}"
            if transaction.id
            else "Trading 212 deposit"
        )

        split = GnuCashSplit(
            date=transaction.time,
            number=transaction.id,
            description=description,
            memo=memo,
            account=self.config.deposit_account,
            value=f"{abs(transaction.total):.2f}",
        )

        return ConversionResult(splits=[split])

    def _convert_interest(self, transaction: Trading212Transaction) -> ConversionResult:
        """Convert an interest payment transaction."""
        description = "Interest on cash from Trading 212"
        if transaction.notes:
            description += f" - {transaction.notes}"

        memo = (
            f"Trading 212 interest - ID: {transaction.id}"
            if transaction.id
            else "Trading 212 interest payment"
        )

        split = GnuCashSplit(
            date=transaction.time,
            number=transaction.id,
            description=description,
            memo=memo,
            account=self.config.interest_account,
            value=f"{abs(transaction.total):.2f}",
        )

        return ConversionResult(splits=[split])

    def _convert_trading_transaction(
        self, transaction: Trading212Transaction
    ) -> ConversionResult:
        """Convert a trading transaction (buy/sell)."""
        splits = []
        warnings = []

        # Validate required fields for trading
        if not all(
            [transaction.num_shares, transaction.price_per_share, transaction.ticker]
        ):
            return ConversionResult(
                splits=[],
                errors=["Missing required trading data (shares, price, or ticker)"],
            )

        # Calculate GBP price per share
        price_gbp = self._calculate_gbp_price(transaction)
        if price_gbp is None:
            warnings.append("Could not calculate GBP price, using original price")
            price_gbp = transaction.price_per_share

        # Get ticker mapping
        gnucash_ticker = self.config.get_gnucash_ticker(transaction.ticker)
        if (
            gnucash_ticker == transaction.ticker
            and transaction.ticker not in self.config.ticker_map
        ):
            warnings.append(f"No ticker mapping found for {transaction.ticker}")

        # Calculate net amount for shares (total minus fees and taxes)
        conversion_fee = transaction.conversion_fee or Decimal("0")
        transaction_tax = transaction.get_transaction_tax() or Decimal("0")
        net_shares_amount = transaction.total - conversion_fee - transaction_tax

        # Create description
        company_display = transaction.name or transaction.ticker
        description = f"{transaction.action} {transaction.num_shares:.6f} shares of {company_display} ({transaction.ticker})"

        # Main share transaction split
        share_split = self._create_share_split(
            transaction, description, gnucash_ticker, net_shares_amount
        )
        splits.append(share_split)

        # Conversion fee split (if non-zero)
        if conversion_fee != 0:
            fee_split = GnuCashSplit(
                date=transaction.time,
                number=transaction.id,
                description=description,
                memo=f"Currency conversion fee for {transaction.ticker}",
                account=self.config.expense_accounts.conversion_fee,
                value=f"{abs(conversion_fee):.2f}",
            )
            splits.append(fee_split)

        # Transaction tax split (if non-zero)
        if transaction_tax != 0:
            tax_type = transaction.get_tax_type()
            tax_account = self.config.get_tax_account(tax_type or "french")

            if tax_type == "french":
                tax_memo = f"French transaction tax for {transaction.ticker}"
            elif tax_type == "stamp_duty":
                tax_memo = f"Stamp duty reserve tax for {transaction.ticker}"
            else:
                tax_memo = f"Transaction tax for {transaction.ticker}"

            tax_split = GnuCashSplit(
                date=transaction.time,
                number=transaction.id,
                description=description,
                memo=tax_memo,
                account=tax_account,
                value=f"{abs(transaction_tax):.2f}",
            )
            splits.append(tax_split)

        return ConversionResult(splits=splits, warnings=warnings)

    def _create_share_split(
        self,
        transaction: Trading212Transaction,
        description: str,
        gnucash_ticker: str,
        net_amount: Decimal,
    ) -> GnuCashSplit:
        """Create the main share transaction split."""
        if transaction.is_buy_action():
            memo = f"Purchase of {transaction.num_shares:.6f} shares @ {gnucash_ticker}"
            amount = f"{transaction.num_shares:.6f}"
        else:  # sell action
            memo = f"Sale of {transaction.num_shares:.6f} shares @ {gnucash_ticker}"
            amount = f"-{transaction.num_shares:.6f}"

        return GnuCashSplit(
            date=transaction.time,
            number=transaction.id,
            description=description,
            memo=memo,
            account=transaction.name or transaction.ticker or "Unknown",
            transaction_commodity=gnucash_ticker,
            amount=amount,
            value=f"{abs(net_amount):.2f}",
        )

    def _calculate_gbp_price(
        self, transaction: Trading212Transaction
    ) -> Optional[Decimal]:
        """Calculate GBP price per share using available exchange rate data."""
        # Method 1: Use exchange rate if available
        if (
            transaction.price_currency
            and transaction.price_currency != "GBP"
            and transaction.exchange_rate
            and transaction.exchange_rate != 0
        ):
            return transaction.price_per_share / transaction.exchange_rate

        # Method 2: Calculate from total amount
        if (
            transaction.total_currency == "GBP"
            and transaction.num_shares
            and transaction.num_shares != 0
        ):
            return abs(transaction.total) / transaction.num_shares

        # Method 3: Assume already in GBP
        return transaction.price_per_share

    def convert_file(
        self, input_file: Union[str, Path], output_file: Union[str, Path]
    ) -> bool:
        """Convert entire Trading212 CSV file to GnuCash format."""
        input_file = Path(input_file)
        output_file = Path(output_file)

        if not self.validate_csv_file(input_file):
            return False

        try:
            # GnuCash multi-split CSV headers
            headers = [
                "Date",
                "Number",
                "Description",
                "Memo",
                "Account",
                "Transaction Commodity",
                "Amount",
                "Value",
            ]

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()

                processed_count = 0
                error_count = 0
                warning_count = 0

                for transaction in self.read_transactions(input_file):
                    result = self.convert_transaction(transaction)

                    if result.errors:
                        error_count += len(result.errors)
                        for error in result.errors:
                            self.logger.error(f"Transaction {transaction.id}: {error}")
                        continue

                    if result.warnings:
                        warning_count += len(result.warnings)
                        for warning in result.warnings:
                            self.logger.warning(
                                f"Transaction {transaction.id}: {warning}"
                            )

                    # Write all splits for this transaction
                    for split in result.splits:
                        writer.writerow(split.to_dict())

                    processed_count += 1

                self.logger.info(
                    f"Successfully processed {processed_count} transactions"
                )
                if error_count > 0:
                    self.logger.warning(f"Encountered {error_count} errors")
                if warning_count > 0:
                    self.logger.info(f"Generated {warning_count} warnings")

                self.logger.info(f"Output written to: {output_file}")
                return True

        except Exception as e:
            self.logger.error(f"Error processing file: {e}")
            return False
