# Trading212 CSV to GnuCash Converter

A modern Python tool that converts Trading212 CSV export files into a format suitable for importing into GnuCash. The converter creates multi-split transactions with separate entries for shares, currency conversion fees, and transaction taxes, with proper GBP currency conversion.

## Features

- 🚀 **Modern CLI Interface** - Easy-to-use command-line interface with helpful options
- ⚙️ **Configurable Mappings** - Customize ticker symbols and account mappings via YAML config
- 💱 **Automatic Currency Conversion** - Converts prices to GBP using Trading212's exchange rates
- 📊 **GnuCash Stock Import Ready** - Includes Price and Transaction Commodity columns for proper stock transactions
- 🔄 **Multi-Split Transactions** - Creates proper multi-split entries for shares, fees, and taxes
- 🛡️ **Error Handling** - Robust validation and error reporting
- 📝 **Detailed Logging** - Comprehensive logging with optional verbose mode
- 🔧 **Minimal Dependencies** - Only requires PyYAML (Python 3.7+)

## Quick Start

### 1. Basic Usage

Convert a Trading212 CSV file to GnuCash format:

```bash
python3 trading212_converter.py input.csv output.csv
```

### 2. Create Configuration File

Generate a sample configuration file to customize ticker and account mappings:

```bash
python3 trading212_converter.py --create-config
```

This creates `trading212_config.yaml` with sample mappings that you can edit.

### 3. Use Custom Configuration

```bash
python3 trading212_converter.py input.csv output.csv --config my_config.yaml
```

### 4. Verbose Logging

Enable detailed logging for troubleshooting:

```bash
python3 trading212_converter.py input.csv output.csv --verbose
```

## Configuration

The tool uses a YAML configuration file to:
- Map Trading212 ticker symbols to Yahoo Finance symbols (for portfolio tracking)
- Configure expense accounts for fees and taxes

### Sample Configuration (`trading212_config.yaml`)

```yaml
# Trading212 to GnuCash Converter Configuration
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
```

### Configuration Options

- **`ticker_map`**: Maps Trading212 ticker symbols to Yahoo Finance symbols
- **`expense_accounts`**: Defines accounts for fees and taxes

**Note**: For share transactions, the Transfer Account uses the company name directly (e.g., "Microsoft Corporation"). GnuCash will map this to the appropriate account during import.

## Input Format

The tool expects Trading212 CSV exports with the following columns:

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
- `Transaction Commodity` - Stock symbol (for stock transactions)

### Currency Conversion

The tool automatically converts prices to GBP using Trading212's exchange rate data:

- **Method 1**: Uses `Exchange rate` field when available: `GBP Price = Original Price ÷ Exchange Rate`
- **Method 2**: Calculates from total: `GBP Price = abs(Total in GBP) ÷ Number of Shares`
- **Fallback**: Uses original price if no conversion data available

### Output Structure

Each Trading212 transaction becomes a multi-split transaction with separate splits for:

1. **Share Transaction** - The number of shares traded
   - **Buy orders**: Positive share quantity (shares acquired)
   - **Sell orders**: Negative share quantity (shares sold)
   - **Price**: Converted to GBP using exchange rate
   - **Transaction Commodity**: Yahoo Finance ticker symbol

2. **Conversion Fee** - Separate split for currency conversion (negative amount, if non-zero)
3. **French Transaction Tax** - Separate split for French tax (negative amount, if non-zero)

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
2025-08-25 07:00:28.695,Market buy 0.905106 shares of Orange (ORA),Orange,0.905106,Purchase of 0.905106 shares @ ORAN.PA,14.5899,ORAN.PA
2025-08-25 07:00:28.695,Market buy 0.905106 shares of Orange (ORA),Expenses:Currency Conversion Fees,-0.02,Currency conversion fee for ORA,,
2025-08-25 07:00:28.695,Market buy 0.905106 shares of Orange (ORA),Expenses:French Transaction Tax,-0.05,French transaction tax for ORA,,
```

This creates one multi-split transaction with three splits:
- **Share purchase**: 0.905106 shares at 14.5899 GBP per share
- **Conversion fee**: -0.02 GBP expense
- **French tax**: -0.05 GBP expense

## Command Line Options

```
usage: trading212_converter.py [-h] [-c CONFIG] [--create-config] [-v] 
                              [input_file] [output_file]

Convert Trading212 CSV exports to GnuCash format

positional arguments:
  input_file            Input Trading212 CSV file
  output_file           Output GnuCash CSV file

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Configuration file path (default: trading212_config.yaml)
  --create-config       Create a sample configuration file and exit
  -v, --verbose         Enable verbose logging

Examples:
  trading212_converter.py input.csv output.csv
  trading212_converter.py input.csv output.csv --config my_config.yaml
  trading212_converter.py --create-config
```

## Installation

### Prerequisites

- Python 3.7 or higher
- PyYAML library

### Setup

1. Clone or download the repository:
   ```bash
   git clone <repository-url>
   cd fix-trading212-csv
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # or just: pip install PyYAML
   ```

3. Make the script executable (optional):
   ```bash
   chmod +x trading212_converter.py
   ```

4. Create your configuration file:
   ```bash
   python3 trading212_converter.py --create-config
   ```

5. Edit the configuration file to match your needs:
   ```bash
   nano trading212_config.yaml
   ```

## Examples

### Example 1: Basic Conversion

```bash
# Convert with default settings
python3 trading212_converter.py trading212_export.csv gnucash_import.csv
```

### Example 2: Custom Configuration

```bash
# Create custom config
python3 trading212_converter.py --create-config --config my_trading_config.yaml

# Use custom config
python3 trading212_converter.py trading212_export.csv gnucash_import.csv --config my_trading_config.yaml
```

### Example 3: Verbose Logging

```bash
# Enable detailed logging for troubleshooting
python3 trading212_converter.py trading212_export.csv gnucash_import.csv --verbose
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
   - Ensure your Trading212 CSV has all required columns
   - Check that column names match exactly (case-sensitive)

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
python3 trading212_converter.py input.csv output.csv --verbose
```

This will show:
- Configuration loading status
- Processing progress
- Currency conversion details
- Warnings for missing mappings
- Detailed error messages

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.