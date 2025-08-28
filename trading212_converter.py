#!/usr/bin/env python3
"""
Trading212 CSV to GnuCash Converter

A modern Python tool to convert Trading212 CSV exports into a format suitable for GnuCash import.
The tool splits transactions into separate rows for shares, stamp duty, and conversion fees.
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
            "ticker_map": {
                "ORA": "ORAN.PA",
                "VOD": "VOD.L",
                "MSFT": "MSFT"
            },
            "account_map": {
                "ORA": "Assets:Investments:Brokerage Account:ORA",
                "VOD": "Assets:Investments:Brokerage Account:VOD",
                "MSFT": "Assets:Investments:Brokerage Account:MSFT"
            },
            "expense_accounts": {
                "stamp_duty": "Expenses:Investment Taxes",
                "conversion_fee": "Expenses:Currency Conversion Fees"
            }
        }
        
        if config_file and config_file.exists():
            try:
                with open(config_file, 'r') as f:
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
            with open(input_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                required_headers = [
                    'Time', 'Ticker', 'Total', 'Stamp duty reserve tax',
                    'Currency conversion fee', 'No. of shares'
                ]
                
                missing_headers = [h for h in required_headers if h not in headers]
                if missing_headers:
                    self.logger.error(f"Missing required headers: {missing_headers}")
                    return False
                    
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
            # Define the headers for the new, transformed CSV
            new_headers = ['Date', 'Description', 'Account', 'Amount', 'Shares', 'Ticker']
            
            with open(input_file, 'r', newline='') as infile, \
                 open(output_file, 'w', newline='') as outfile:
                
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
                        
                self.logger.info(f"Successfully processed {processed_count} transactions")
                self.logger.info(f"Output written to: {output_file}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing file: {e}")
            return False
    
    def _process_row(self, row: Dict, writer: csv.DictWriter) -> None:
        """Process a single row from the Trading212 CSV."""
        # Get data from original row
        time = row['Time']
        ticker = row['Ticker']
        
        try:
            total = float(row['Total'])
            stamp_duty = float(row['Stamp duty reserve tax'])
            conversion_fee = float(row['Currency conversion fee'])
            num_shares = float(row['No. of shares'])
        except ValueError as e:
            raise ValueError(f"Invalid numeric value in row: {e}")
        
        # Perform lookups
        yahoo_ticker = self.config['ticker_map'].get(ticker, ticker)
        account_path = self.config['account_map'].get(ticker, f"Assets:Investments:Brokerage Account:{ticker}")
        
        if ticker not in self.config['ticker_map']:
            self.logger.warning(f"No ticker mapping found for {ticker}, using default")
        if ticker not in self.config['account_map']:
            self.logger.warning(f"No account mapping found for {ticker}, using default")
        
        # Calculate the net amount for the shares
        net_shares_amount = total - stamp_duty - conversion_fee
        
        # Write the transformed rows to the new CSV
        
        # Row for the shares
        writer.writerow({
            'Date': time,
            'Description': ticker,
            'Account': account_path,
            'Amount': f"{net_shares_amount:.2f}",
            'Shares': f"{num_shares:.6f}",
            'Ticker': yahoo_ticker
        })
        
        # Row for the stamp duty fee (only if non-zero)
        if stamp_duty != 0:
            writer.writerow({
                'Date': time,
                'Description': f'{ticker} SDRT',
                'Account': self.config['expense_accounts']['stamp_duty'],
                'Amount': f"{stamp_duty:.2f}",
                'Shares': '',
                'Ticker': ''
            })
        
        # Row for the conversion fee (only if non-zero)
        if conversion_fee != 0:
            writer.writerow({
                'Date': time,
                'Description': f'{ticker} Conv Fee',
                'Account': self.config['expense_accounts']['conversion_fee'],
                'Amount': f"{conversion_fee:.2f}",
                'Shares': '',
                'Ticker': ''
            })


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def create_sample_config(config_path: Path) -> None:
    """Create a sample configuration file."""
    sample_config_yaml = """# Trading212 to GnuCash Converter Configuration
# Edit this file to customize your ticker symbols and account mappings

# Map Trading212 ticker symbols to Yahoo Finance symbols
ticker_map:
  ORA: ORAN.PA      # Orange SA
  VOD: VOD.L        # Vodafone Group PLC
  MSFT: MSFT        # Microsoft Corporation
  AAPL: AAPL        # Apple Inc.
  GOOGL: GOOGL      # Alphabet Inc.

# Map ticker symbols to GnuCash account paths for shares
account_map:
  ORA: "Assets:Investments:Brokerage Account:Orange"
  VOD: "Assets:Investments:Brokerage Account:Vodafone"
  MSFT: "Assets:Investments:Brokerage Account:Microsoft"
  AAPL: "Assets:Investments:Brokerage Account:Apple"
  GOOGL: "Assets:Investments:Brokerage Account:Google"

# GnuCash accounts for fees and taxes
expense_accounts:
  stamp_duty: "Expenses:Investment Taxes"
  conversion_fee: "Expenses:Currency Conversion Fees"
"""
    
    with open(config_path, 'w') as f:
        f.write(sample_config_yaml)
    
    print(f"Sample configuration file created at: {config_path}")
    print("Edit this file to customize your ticker and account mappings.")


def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        description="Convert Trading212 CSV exports to GnuCash format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.csv output.csv
  %(prog)s input.csv output.csv --config my_config.yaml
  %(prog)s --create-config
        """
    )
    
    parser.add_argument(
        'input_file',
        nargs='?',
        type=Path,
        help='Input Trading212 CSV file'
    )
    
    parser.add_argument(
        'output_file',
        nargs='?',
        type=Path,
        help='Output GnuCash CSV file'
    )
    
    parser.add_argument(
        '-c', '--config',
        type=Path,
        default=Path('trading212_config.yaml'),
        help='Configuration file path (default: trading212_config.yaml)'
    )
    
    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create a sample configuration file and exit'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.create_config:
        create_sample_config(args.config)
        return 0
    
    if not args.input_file or not args.output_file:
        parser.error("Input and output files are required (unless using --create-config)")
    
    # Initialize converter
    converter = Trading212Converter(args.config)
    
    # Process the file
    success = converter.process_transactions(args.input_file, args.output_file)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
