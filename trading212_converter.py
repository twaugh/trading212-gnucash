#!/usr/bin/env python3
"""
Trading212 CSV to GnuCash Converter

A modern Python tool to convert Trading212 CSV exports into a format suitable for GnuCash import.
The tool creates multi-split transactions with separate entries for shares, fees, and taxes.
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install it with: pip install PyYAML")
    sys.exit(1)


class Trading212Converter:
    """Main converter class for Trading212 CSV files."""

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize the converter with optional configuration file."""
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_file)

    def _load_config(self, config_file: Optional[Path] = None) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            "ticker_map": {"ORA": "ORAN.PA", "VOD": "VOD.L", "MSFT": "MSFT"},
            "expense_accounts": {
                "conversion_fee": "Expenses:Currency Conversion Fees",
                "french_tax": "Expenses:French Transaction Tax",
                "stamp_duty_tax": "Expenses:Stamp Duty Reserve Tax",
            },
            "deposit_account": "Assets:Trading212 Deposits",
            "interest_account": "Income:Trading212 Interest",
        }

        if config_file and config_file.exists():
            try:
                with open(config_file, "r") as f:
                    user_config = yaml.safe_load(f)
                    # Merge user config with defaults
                    for key, value in user_config.items():
                        if isinstance(value, dict) and key in default_config:
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
                self.logger.info(f"Loaded configuration from {config_file}")
            except (yaml.YAMLError, IOError) as e:
                self.logger.error(f"Error loading config file: {e}")
                self.logger.info("Using default configuration")
        else:
            self.logger.info("Using default configuration")

        return default_config

    def _validate_input_file(self, input_file: Path) -> bool:
        """Validate that the input file exists and has the expected format."""
        if not input_file.exists():
            self.logger.error(f"Input file does not exist: {input_file}")
            return False

        try:
            with open(input_file, "r", newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                # Core required headers that should always be present
                core_required_headers = [
                    "Action",
                    "Time",
                    "ISIN",
                    "Ticker",
                    "Name",
                    "Notes",
                    "ID",
                ]

                # Trading-specific headers (required for buy/sell transactions)
                trading_headers = [
                    "No. of shares",
                    "Price / share",
                    "Currency (Price / share)",
                    "Exchange rate",
                    "Currency (Result)",
                    "Total",
                    "Currency (Total)",
                ]

                # Optional fee/tax headers (may or may not be present)
                optional_fee_headers = [
                    "Currency conversion fee",
                    "Currency (Currency conversion fee)",
                    "French transaction tax",
                    "Currency (French transaction tax)",
                    "Stamp duty reserve tax",
                    "Currency (Stamp duty reserve tax)",
                ]

                # Check for core headers
                missing_core = [h for h in core_required_headers if h not in headers]
                if missing_core:
                    self.logger.error(f"Missing core required headers: {missing_core}")
                    return False

                # Log which headers are present for debugging
                self.logger.info(
                    f"CSV contains {len(headers)} columns: {', '.join(headers)}"
                )

                # Check if we have trading headers (for transactions other than deposits)
                has_trading_headers = all(h in headers for h in trading_headers)
                if not has_trading_headers:
                    self.logger.warning(
                        "Some trading headers are missing. This may cause issues with buy/sell transactions."
                    )
                    self.logger.debug(
                        f"Missing trading headers: {[h for h in trading_headers if h not in headers]}"
                    )

                # Log which optional fee headers are present
                present_fee_headers = [h for h in optional_fee_headers if h in headers]
                if present_fee_headers:
                    self.logger.info(
                        f"Fee/tax columns present: {', '.join(present_fee_headers)}"
                    )

        except Exception as e:
            self.logger.error(f"Error reading input file: {e}")
            return False

        return True

    def process_transactions(self, input_file: Path, output_file: Path) -> bool:
        """
        Process Trading212 CSV file and convert to GnuCash format.

        Args:
            input_file: Path to the Trading212 CSV file
            output_file: Path for the output GnuCash CSV file

        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not self._validate_input_file(input_file):
            return False

        try:
            # Define headers for GnuCash multi-split import
            new_headers = [
                "Date",
                "Number",
                "Description",
                "Memo",
                "Account",
                "Transaction Commodity",
                "Amount",
                "Value",
            ]

            with open(input_file, "r", newline="") as infile, open(
                output_file, "w", newline=""
            ) as outfile:

                reader = csv.DictReader(infile)
                writer = csv.DictWriter(outfile, fieldnames=new_headers)
                writer.writeheader()

                processed_count = 0

                for row_num, row in enumerate(reader, 1):
                    try:
                        self._process_row(row, writer)
                        processed_count += 1
                    except Exception as e:
                        self.logger.error(f"Error processing row {row_num}: {e}")
                        self.logger.debug(f"Row data: {row}")
                        continue

                self.logger.info(
                    f"Successfully processed {processed_count} transactions"
                )
                self.logger.info(f"Output written to: {output_file}")
                return True

        except Exception as e:
            self.logger.error(f"Error processing file: {e}")
            return False

    def _process_row(self, row: Dict, writer: csv.DictWriter) -> None:
        """Process a single row from the Trading212 CSV into multi-split format."""
        # Get basic data from original row
        action = row["Action"]
        time = row["Time"]
        transaction_id = row.get("ID", "")

        # Parse total amount (required for all transaction types)
        try:
            total = float(row["Total"]) if row["Total"] else 0.0
        except ValueError as e:
            raise ValueError(f"Invalid total amount in row: {e}")

        # Handle simple transaction types first (don't need trading-specific fields)
        if action == "Deposit":
            self._process_deposit(row, writer, time, total, action, transaction_id)
            return
        elif action == "Interest on cash":
            self._process_interest(row, writer, time, total, action, transaction_id)
            return
        elif action in ["Market buy", "Market sell", "Limit buy", "Limit sell"]:
            # Continue processing trading actions below
            pass
        else:
            # Error on unknown actions
            raise ValueError(
                f"Unknown action type: '{action}'. Supported actions are: Deposit, Interest on cash, Market buy, Market sell, Limit buy, Limit sell"
            )

        # For trading actions, we need additional fields
        isin = row["ISIN"]
        ticker = row["Ticker"]
        name = row["Name"]

        try:
            conversion_fee = (
                float(row["Currency conversion fee"])
                if row.get("Currency conversion fee")
                else 0.0
            )
            num_shares = float(row["No. of shares"]) if row["No. of shares"] else 0.0
            price_per_share_original = (
                float(row["Price / share"]) if row["Price / share"] else 0.0
            )
            exchange_rate = float(row["Exchange rate"]) if row["Exchange rate"] else 1.0

            # Handle different tax column names flexibly
            transaction_tax = 0.0
            if row.get("French transaction tax"):
                transaction_tax = float(row["French transaction tax"])
            elif row.get("Stamp duty reserve tax"):
                transaction_tax = float(row["Stamp duty reserve tax"])

        except ValueError as e:
            raise ValueError(f"Invalid numeric value in row: {e}")

        # Get currency information
        price_currency = row.get("Currency (Price / share)", "")
        total_currency = row.get("Currency (Total)", "")

        # Calculate GBP price per share
        # If we have exchange rate information and the price is not already in GBP
        if price_currency and price_currency != "GBP" and exchange_rate != 0:
            # Convert original price to GBP using exchange rate
            price_per_share_gbp = price_per_share_original / exchange_rate
        elif total_currency == "GBP" and num_shares != 0:
            # Use the total amount method as fallback (total should be in GBP)
            price_per_share_gbp = abs(total) / num_shares
        else:
            # Assume price is already in GBP or no conversion needed
            price_per_share_gbp = price_per_share_original

        # Perform lookups for trading actions
        yahoo_ticker = self.config["ticker_map"].get(ticker, ticker)
        # Get the unified transfer account (deposit account) for all transactions
        transfer_account = self.config.get(
            "deposit_account", "Assets:Trading212 Deposits"
        )
        # Use company name for the specific Account field
        company_name = name if name else ticker

        if ticker not in self.config["ticker_map"]:
            self.logger.warning(f"No ticker mapping found for {ticker}, using default")

        # Calculate the net amount for the shares
        net_shares_amount = total - conversion_fee - transaction_tax

        # Create transaction description (shared by all splits)
        description = (
            f"{action} {num_shares:.6f} shares of {name} ({ticker})"
            if name
            else f"{action} {num_shares:.6f} shares of {ticker}"
        )

        # Write multi-split transaction rows
        # All splits share the same date and description, but different Transfer Accounts

        # Split 1: Main transaction (buy/sell shares)
        # For multi-split: Transfer Account is the destination (source account set during GnuCash import)
        if action in ["Market buy", "Limit buy"]:
            # Buy: Positive number of shares being purchased
            writer.writerow(
                {
                    "Date": time,
                    "Number": transaction_id,
                    "Description": description,
                    "Memo": f"Purchase of {num_shares:.6f} shares @ {yahoo_ticker}",
                    "Account": company_name,
                    "Transaction Commodity": yahoo_ticker,
                    "Amount": f"{num_shares:.6f}",
                    "Value": f"{abs(net_shares_amount):.2f}",
                }
            )
        else:  # Market sell, Limit sell
            # Sell: Negative number of shares being sold
            writer.writerow(
                {
                    "Date": time,
                    "Number": transaction_id,
                    "Description": description,
                    "Memo": f"Sale of {num_shares:.6f} shares @ {yahoo_ticker}",
                    "Account": company_name,
                    "Transaction Commodity": yahoo_ticker,
                    "Amount": f"-{num_shares:.6f}",
                    "Value": f"{abs(net_shares_amount):.2f}",
                }
            )

        # Split 2: Conversion fee (only if non-zero)
        if conversion_fee != 0:
            writer.writerow(
                {
                    "Date": time,
                    "Number": transaction_id,
                    "Description": description,
                    "Memo": f"Currency conversion fee for {ticker}",
                    "Account": self.config["expense_accounts"]["conversion_fee"],
                    "Transaction Commodity": "",
                    "Amount": "",  # Empty amount for expense transactions
                    "Value": f"{abs(conversion_fee):.2f}",  # Positive value for expense cost
                }
            )

        # Split 3: Transaction tax (French tax or Stamp duty, only if non-zero)
        if transaction_tax != 0:
            # Determine which tax type we're dealing with
            if row.get("French transaction tax"):
                tax_account = self.config["expense_accounts"]["french_tax"]
                tax_memo = f"French transaction tax for {ticker}"
            elif row.get("Stamp duty reserve tax"):
                tax_account = self.config["expense_accounts"]["stamp_duty_tax"]
                tax_memo = f"Stamp duty reserve tax for {ticker}"
            else:
                # Fallback to French tax account if we can't determine the type
                tax_account = self.config["expense_accounts"]["french_tax"]
                tax_memo = f"Transaction tax for {ticker}"

            writer.writerow(
                {
                    "Date": time,
                    "Number": transaction_id,
                    "Description": description,
                    "Memo": tax_memo,
                    "Account": tax_account,
                    "Transaction Commodity": "",
                    "Amount": "",  # Empty amount for expense transactions
                    "Value": f"{abs(transaction_tax):.2f}",  # Positive value for expense cost
                }
            )

    def _process_deposit(
        self, row: Dict, writer: csv.DictWriter, time: str, total: float, action: str, transaction_id: str
    ) -> None:
        """Process a deposit transaction from Trading212."""
        # Extract deposit information
        notes = row.get("Notes", "")

        # Create description for deposit
        description = f"Deposit from Trading212"
        if notes:
            description += f" - {notes}"

        # Get deposit account from configuration
        deposit_source = self.config.get(
            "deposit_account", "Assets:Trading212 Deposits"
        )

        # Write the deposit transaction
        # Positive amount as money is coming into the account
        writer.writerow(
            {
                "Date": time,
                "Number": transaction_id,
                "Description": description,
                "Memo": (
                    f"Trading212 deposit - ID: {transaction_id}"
                    if transaction_id
                    else "Trading212 deposit"
                ),
                "Account": deposit_source,  # Specific account for this deposit
                "Transaction Commodity": "",
                "Amount": f"{abs(total):.2f}",  # Positive amount (money coming in)
                "Value": f"{abs(total):.2f}",  # Value is the deposit amount
            }
        )

    def _process_interest(
        self, row: Dict, writer: csv.DictWriter, time: str, total: float, action: str, transaction_id: str
    ) -> None:
        """Process an interest on cash transaction from Trading212."""
        # Extract interest information
        notes = row.get("Notes", "")

        # Create description for interest
        description = f"Interest on cash from Trading212"
        if notes:
            description += f" - {notes}"

        # Get interest account from configuration
        interest_account = self.config.get(
            "interest_account", "Income:Trading212 Interest"
        )

        # Write the interest transaction
        # Positive amount as this is income
        writer.writerow(
            {
                "Date": time,
                "Number": transaction_id,
                "Description": description,
                "Memo": (
                    f"Trading212 interest - ID: {transaction_id}"
                    if transaction_id
                    else "Trading212 interest payment"
                ),
                "Account": interest_account,
                "Transaction Commodity": "",
                "Amount": f"{abs(total):.2f}",  # Positive amount (income)
                "Value": f"{abs(total):.2f}",  # Value is the interest amount
            }
        )


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def create_sample_config(config_path: Path) -> None:
    """Create a sample configuration file."""
    sample_config_yaml = """# Trading212 to GnuCash Multi-Split Converter Configuration
# Edit this file to customize your ticker symbols and account mappings

# Map Trading212 ticker symbols to Yahoo Finance symbols
ticker_map:
  ORA: ORAN.PA      # Orange SA
  VOD: VOD.L        # Vodafone Group PLC
  MSFT: MSFT        # Microsoft Corporation
  AAPL: AAPL        # Apple Inc.
  GOOGL: GOOGL      # Alphabet Inc.

# GnuCash accounts for fees and taxes
# Note: For share transactions, Transfer Account uses company name directly (e.g., "Microsoft Corporation")
# Note: Source account (where money comes from/goes to) is configured during GnuCash import
expense_accounts:
  conversion_fee: "Expenses:Currency Conversion Fees"
  french_tax: "Expenses:French Transaction Tax"
  stamp_duty_tax: "Expenses:Stamp Duty Reserve Tax"

# Account for deposits from Trading212
deposit_account: "Assets:Trading212 Deposits"

# Account for interest on cash from Trading212
interest_account: "Income:Trading212 Interest"
"""

    with open(config_path, "w") as f:
        f.write(sample_config_yaml)

    print(f"Sample configuration file created at: {config_path}")
    print("Edit this file to customize your ticker and account mappings.")
    print(
        "The source account (bank/cash account) will be configured during GnuCash import."
    )


def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        description="Convert Trading212 CSV exports to GnuCash multi-split format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.csv output.csv
  %(prog)s input.csv output.csv --config my_config.yaml
  %(prog)s --create-config

This tool creates multi-split transactions suitable for GnuCash import.
Each Trading212 transaction becomes a multi-split transaction with:
- Money transfer between your source account and investment accounts
- Separate splits for fees and taxes
The source account is configured during the GnuCash import process.
        """,
    )

    parser.add_argument(
        "input_file", nargs="?", type=Path, help="Input Trading212 CSV file"
    )

    parser.add_argument(
        "output_file", nargs="?", type=Path, help="Output GnuCash CSV file"
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("trading212_config.yaml"),
        help="Configuration file path (default: trading212_config.yaml)",
    )

    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a sample configuration file and exit",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.create_config:
        create_sample_config(args.config)
        return 0

    if not args.input_file or not args.output_file:
        parser.error(
            "Input and output files are required (unless using --create-config)"
        )

    # Initialize converter
    converter = Trading212Converter(args.config)

    # Process the file
    success = converter.process_transactions(args.input_file, args.output_file)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
