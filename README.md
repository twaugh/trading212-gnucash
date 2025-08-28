# Trading212 CSV to GnuCash Converter

A modern Python tool that converts Trading212 CSV export files into a format suitable for importing into GnuCash. The converter splits each transaction into separate entries for shares, stamp duty reserve tax, and currency conversion fees.

## Features

- 🚀 **Modern CLI Interface** - Easy-to-use command-line interface with helpful options
- ⚙️ **Configurable Mappings** - Customize ticker symbols and account mappings via YAML config
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

The tool uses a YAML configuration file to map Trading212 ticker symbols to:
- Yahoo Finance ticker symbols (for portfolio tracking)
- GnuCash account paths

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
```

### Configuration Options

- **`ticker_map`**: Maps Trading212 ticker symbols to Yahoo Finance symbols
- **`account_map`**: Maps ticker symbols to GnuCash account paths for the shares
- **`expense_accounts`**: Defines accounts for fees and taxes

## Input Format

The tool expects Trading212 CSV exports with the following required columns:

- `Time` - Transaction timestamp
- `Ticker` - Stock ticker symbol
- `Total` - Total transaction amount
- `Stamp duty reserve tax` - SDRT amount
- `Currency conversion fee` - Conversion fee amount
- `No. of shares` - Number of shares traded

## Output Format

The converter creates a GnuCash-compatible CSV with these columns:

- `Date` - Transaction date
- `Description` - Transaction description
- `Account` - GnuCash account path
- `Amount` - Transaction amount
- `Shares` - Number of shares (for share transactions only)
- `Ticker` - Yahoo Finance ticker symbol (for share transactions only)

### Output Structure

Each Trading212 transaction becomes multiple GnuCash entries:

1. **Share Transaction** - The net amount for the actual shares
2. **Stamp Duty** - Separate entry for SDRT (if non-zero)
3. **Conversion Fee** - Separate entry for currency conversion (if non-zero)

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

### Getting Help

Run with `--verbose` flag to see detailed processing information:

```bash
python3 trading212_converter.py input.csv output.csv --verbose
```

This will show:
- Configuration loading status
- Processing progress
- Warnings for missing mappings
- Detailed error messages

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.
