[![CI](https://github.com/twaugh/trading212-gnucash/actions/workflows/ci.yml/badge.svg)](https://github.com/twaugh/trading212-gnucash/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/twaugh/trading212-gnucash/branch/main/graph/badge.svg)](https://codecov.io/gh/twaugh/trading212-gnucash)

# Trading 212 to GnuCash Converter

A modern Python tool that converts Trading 212 CSV export files into a format suitable for importing into GnuCash. The converter creates multi-split transactions with separate entries for shares, currency conversion fees, and transaction taxes, with proper GBP currency conversion.

## Features

- ⚙️ **Configurable Mappings** - Customize ticker symbols and account mappings via YAML config
- 📊 **GnuCash Stock Import Ready** - Includes Price and Transaction Commodity columns for proper stock transactions
- 🔄 **Multi-Split Transactions** - Creates proper multi-split entries for shares, fees, and taxes
- 🛡️ **Type Safety** - Built with Pydantic models for robust data validation
- 📝 **Rich Logging** - Beautiful logging with Rich library and detailed error reporting

## Installation

### From Source

```bash
git clone https://github.com/twaugh/trading212-gnucash
cd trading212-gnucash
pip install .
```

### Development Installation

```bash
git clone https://github.com/twaugh/trading212-gnucash
cd trading212-gnucash
pip install -e ".[dev]"
```

## Quick Start

### 1. Create Configuration File

Generate a sample configuration file to customize ticker and account mappings:

```bash
trading212-gnucash init-config
```

This creates `~/.config/trading212-gnucash/config.yaml` with sample mappings that you can edit.

### 2. Basic Usage

Convert a Trading 212 CSV file to GnuCash format:

```bash
trading212-gnucash convert input.csv output.csv
```

### 3. Use Custom Configuration

```bash
trading212-gnucash convert input.csv output.csv --config my_config.yaml
```

### 4. Verbose Logging

Enable detailed logging for troubleshooting:

```bash
trading212-gnucash convert input.csv output.csv --verbose
```

### 5. Analyze Your Data

Get information about your Trading212 CSV file:

```bash
trading212-gnucash info input.csv
```

## Configuration

The tool uses a YAML configuration file located at `~/.config/trading212-gnucash/config.yaml` to:
- Map Trading 212 ticker symbols to GnuCash stock symbols (which may include exchange suffixes)
- Configure expense accounts for fees and taxes

### Sample Configuration

```yaml
# Trading 212 to GnuCash Converter Configuration
# Edit this file to customize your ticker symbols and account mappings

# Map Trading 212 ticker symbols to GnuCash stock symbols
ticker_map:
  ACME: ACME.L      # Acme Corporation Ltd (London exchange)
  VOD: VOD.L        # Vodafone Group PLC (London exchange)
  MSFT: MSFT        # Microsoft Corporation (NASDAQ)
  AAPL: AAPL        # Apple Inc. (NASDAQ)
  GOOGL: GOOGL      # Alphabet Inc. (NASDAQ)

# GnuCash accounts for fees and taxes
# Note: For share transactions, Transfer Account uses company name directly (e.g., "Microsoft Corporation")
# Note: Source account (where money comes from/goes to) is configured during GnuCash import
expense_accounts:
  conversion_fee: "Expenses:Currency Conversion Fees"
  french_tax: "Expenses:French Transaction Tax"
```

### Configuration File Locations

The tool looks for configuration files in the following order:

1. `~/.config/trading212-gnucash/config.yaml` (recommended)
2. `~/.config/trading212-gnucash/config.yml`
3. `trading212_config.yaml` (current directory, legacy)
4. `trading212_config.yml` (current directory, legacy)
5. `~/.trading212_config.yaml` (home directory, legacy)

### Configuration Options

- **`ticker_map`**: Maps Trading 212 ticker symbols to GnuCash stock symbols (may include exchange suffixes like .L, .PA, etc.)
- **`expense_accounts`**: Defines accounts for fees and taxes
- **`deposit_account`**: Account for Trading 212 deposits
- **`interest_account`**: Account for interest payments

**Notes**: 
- For share transactions, the Transfer Account uses the company name directly (e.g., "Microsoft Corporation"). GnuCash will map this to the appropriate account during import.
- The ticker symbols in the mapping should match exactly what you have configured in GnuCash for each stock, including any exchange suffixes (e.g., `.L` for London Stock Exchange, `.PA` for Euronext Paris).

## Input Format

The tool expects Trading 212 CSV exports with the following columns:

- `Action` - Transaction type (Market buy, Market sell, etc.)
- `Time` - Transaction timestamp
- `ISIN` - International Securities Identification Number
- `Ticker` - Stock ticker symbol
- `Name` - Full company name
- `Notes` - Additional notes
- `ID` - Transaction ID
- `No. of shares` - Number of shares traded
- `Price / share` - Price per share (in original currency)
- `Currency (Price / share)` - Currency of share price
- `Exchange rate` - Exchange rate used for conversion
- `Currency (Result)` - Result currency
- `Total` - Total transaction amount (in GBP)
- `Currency (Total)` - Currency of total amount
- `Currency conversion fee` - Conversion fee amount
- `Currency (Currency conversion fee)` - Currency of conversion fee
- `French transaction tax` - French transaction tax amount
- `Currency (French transaction tax)` - Currency of French tax

## Output Format

The converter creates a GnuCash-compatible CSV for multi-split import with these columns:

- `Date` - Transaction date
- `Description` - Transaction description (shared by all splits)
- `Transfer Account` - Destination account for each split
- `Amount` - Transaction amount or share quantity
- `Memo` - Additional details for each split
- `Price` - Price per share in GBP (for stock transactions)
- `Transaction Commodity` - Stock symbol as configured in GnuCash (for stock transactions)

### Output Structure

Each Trading 212 transaction becomes a multi-split transaction with separate splits for:

1. **Share Transaction** - The number of shares traded
   - **Buy orders**: Positive share quantity (shares acquired)
   - **Sell orders**: Negative share quantity (shares sold)
   - **Price**: Converted to GBP using exchange rate
   - **Transaction Commodity**: Yahoo Finance ticker symbol

2. **Conversion Fee** - Separate split for currency conversion (negative amount, if non-zero)
3. **Transaction Tax** - Separate split for tax (negative amount, if non-zero)

All splits share the same `Date` and `Description`, creating a single multi-split transaction.

### GnuCash Multi-Split Import

The output CSV is designed for GnuCash's stock transaction import feature:
- **Transfer Account** specifies the destination for each split
- **Amount** column contains share quantities for stock transactions, negative amounts for fees
- **Price** column contains GBP price per share for proper stock valuation
- **Transaction Commodity** identifies the stock symbol
- **Memo** provides additional context for each split

During GnuCash import:
1. Set the source account (e.g., your checking account) in the Account field
2. GnuCash will automatically create multi-split transactions
3. Stock transactions will use the Price and Transaction Commodity for proper accounting
4. Fee transactions will be recorded as expenses

### Sample Output

```csv
Date,Description,Transfer Account,Amount,Memo,Price,Transaction Commodity
2025-08-25 07:00:28.695,Market buy 0.905106 shares of Acme Corporation (ACME),Acme Corporation,0.905106,Purchase of 0.905106 shares @ ACME.L,14.5899,ACME.L
2025-08-25 07:00:28.695,Market buy 0.905106 shares of Acme Corporation (ACME),Expenses:Currency Conversion Fees,-0.02,Currency conversion fee for ACME,,
2025-08-25 07:00:28.695,Market buy 0.905106 shares of Acme Corporation (ACME),Expenses:French Transaction Tax,-0.05,French transaction tax for ACME,,
```

This creates one multi-split transaction with three splits:
- **Share purchase**: 0.905106 shares at 14.5899 GBP per share
- **Conversion fee**: -0.02 GBP expense
- **French tax**: -0.05 GBP expense

## Command Line Interface

The tool provides several commands for different operations:

### Main Commands

```bash
# Convert CSV files
trading212-gnucash convert input.csv output.csv

# Create sample configuration
trading212-gnucash init-config

# Analyze CSV file
trading212-gnucash info input.csv

# Validate configuration
trading212-gnucash validate-config

# Show help
trading212-gnucash --help
```

### Command Options

#### Convert Command
```bash
trading212-gnucash convert [OPTIONS] INPUT_FILE OUTPUT_FILE

Options:
  -c, --config PATH    Configuration file path
  -v, --verbose        Enable verbose logging
  --validate-only      Only validate input file, don't convert
  --help              Show help and exit
```

#### Init-Config Command
```bash
trading212-gnucash init-config [OPTIONS]

Options:
  -c, --config PATH    Configuration file path to create
  --force             Overwrite existing configuration file
  --help              Show help and exit
```

## Development

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

### Setup for Development

1. Clone the repository:
   ```bash
   git clone https://github.com/twaugh/trading212-gnucash
   cd trading212-gnucash
   ```

2. Install in development mode with dev dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest
   ```

4. Run type checking:
   ```bash
   mypy src/
   ```

5. Format code:
   ```bash
   black src/ tests/
   ruff check src/ tests/
   ```

## Examples

### Example 1: Basic Conversion

```bash
# Convert with default settings
trading212-gnucash convert trading212_export.csv gnucash_import.csv
```

### Example 2: Custom Configuration

```bash
# Create custom config in a specific location
trading212-gnucash init-config --config ~/my_trading_config.yaml

# Use custom config
trading212-gnucash convert trading212_export.csv gnucash_import.csv --config ~/my_trading_config.yaml

# Or use the default config location (recommended)
trading212-gnucash init-config  # Creates ~/.config/trading212-gnucash/config.yaml
trading212-gnucash convert trading212_export.csv gnucash_import.csv  # Uses default config
```

### Example 3: Verbose Logging

```bash
# Enable detailed logging for troubleshooting
trading212-gnucash convert trading212_export.csv gnucash_import.csv --verbose
```

### Example 4: File Analysis

```bash
# Analyze your Trading 212 CSV file before conversion
trading212-gnucash info trading212_export.csv
```

## Currency Conversion Details

The converter handles multiple currency scenarios:

### EUR to GBP Example
- **Original price**: 12.47 EUR per share
- **Exchange rate**: 0.8547 (EUR to GBP)
- **GBP price**: 12.47 ÷ 0.8547 = 14.5899 GBP per share

### USD to GBP Example
- **Original price**: 150.00 USD per share  
- **Exchange rate**: 0.7850 (USD to GBP)
- **GBP price**: 150.00 ÷ 0.7850 = 191.08 GBP per share

The tool automatically detects the source currency and applies the appropriate conversion.

## Troubleshooting

### Common Issues

1. **Missing Required Headers**
   - Ensure your Trading 212 CSV has all required columns
   - Check that column names match exactly (case-sensitive)
   - Note: Some columns (like ISIN, Ticker, Name) may be empty for non-trading transactions (deposits, interest) - this is normal

2. **Invalid Numeric Values**
   - Verify that numeric columns contain valid numbers
   - Check for unexpected formatting in amount fields

3. **Configuration File Errors**
   - Validate YAML syntax in your config file
   - Ensure all required sections are present

4. **Currency Conversion Issues**
   - Verify that Exchange rate column contains valid numbers
   - Check Currency columns for correct currency codes

### Getting Help

Run with `--verbose` flag to see detailed processing information:

```bash
trading212-gnucash convert input.csv output.csv --verbose
```

This will show:
- Configuration loading status
- Processing progress
- Currency conversion details
- Warnings for missing mappings
- Detailed error messages

## License

This project is licensed under the GNU General Public License v3.0 or later (GPLv3+). See the [LICENSE](LICENSE) file for details.

This ensures that the software remains free and open source, and any derivative works must also be distributed under the same license terms.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Start for Contributors

1. Fork the repository
2. Set up development environment: `pip install -e ".[dev]"`
3. Run tests: `pytest --cov`
4. Make your changes and add tests
5. Submit a pull request

### Reporting Issues

- **Bug reports**: Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md)
- **Feature requests**: Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
