"""Configuration management for Trading 212 to GnuCash converter.

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
from pathlib import Path
from typing import Dict, Optional, Union
import yaml
from pydantic import BaseModel, Field, validator


class ExpenseAccounts(BaseModel):
    """Configuration for expense accounts."""
    
    conversion_fee: str = Field(
        default="Expenses:Currency Conversion Fees",
        description="Account for currency conversion fees"
    )
    french_tax: str = Field(
        default="Expenses:French Transaction Tax", 
        description="Account for French transaction tax"
    )
    stamp_duty_tax: str = Field(
        default="Expenses:Stamp Duty Reserve Tax",
        description="Account for UK stamp duty reserve tax"
    )


class Config(BaseModel):
    """Main configuration model."""
    
    ticker_map: Dict[str, str] = Field(
        default_factory=lambda: {
            "ACME": "ACME.L",
            "VOD": "VOD.L", 
            "MSFT": "MSFT",
            "AAPL": "AAPL",
            "GOOGL": "GOOGL"
        },
        description="Map Trading 212 ticker symbols to GnuCash stock symbols"
    )
    
    expense_accounts: ExpenseAccounts = Field(
        default_factory=ExpenseAccounts,
        description="Configuration for expense accounts"
    )
    
    deposit_account: str = Field(
        default="Assets:Trading 212 Deposits",
        description="Account for deposits from Trading 212"
    )
    
    interest_account: str = Field(
        default="Income:Trading 212 Interest",
        description="Account for interest on cash from Trading 212"
    )
    
    @classmethod
    def load_from_file(cls, config_path: Optional[Union[str, Path]] = None) -> "Config":
        """Load configuration from file with fallback to defaults."""
        if config_path is None:
            # Try common config file locations in order of preference
            possible_paths = [
                Path("~/.config/trading212-gnucash/config.yaml").expanduser(),
                Path("~/.config/trading212-gnucash/config.yml").expanduser(),
                Path("trading212_config.yaml"),  # Current directory fallback
                Path("trading212_config.yml"),   # Current directory fallback
                Path("~/.trading212_config.yaml").expanduser(),  # Legacy location
            ]
            
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
        
        if config_path is None:
            return cls()  # Use defaults
            
        config_path = Path(config_path)
        
        if not config_path.exists():
            return cls()  # Use defaults
            
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
            if data is None:
                return cls()
                
            return cls(**data)
            
        except (yaml.YAMLError, ValueError) as e:
            raise ValueError(f"Error loading config file {config_path}: {e}")
    
    @classmethod
    def load_from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config_data = {}
        
        # Load ticker mappings from environment
        ticker_map = {}
        for key, value in os.environ.items():
            if key.startswith("TRADING212_TICKER_"):
                ticker = key.replace("TRADING212_TICKER_", "")
                ticker_map[ticker] = value
        
        if ticker_map:
            config_data["ticker_map"] = ticker_map
        
        # Load account configurations
        if os.getenv("TRADING212_DEPOSIT_ACCOUNT"):
            config_data["deposit_account"] = os.getenv("TRADING212_DEPOSIT_ACCOUNT")
            
        if os.getenv("TRADING212_INTEREST_ACCOUNT"):
            config_data["interest_account"] = os.getenv("TRADING212_INTEREST_ACCOUNT")
        
        # Load expense accounts
        expense_accounts = {}
        if os.getenv("TRADING212_CONVERSION_FEE_ACCOUNT"):
            expense_accounts["conversion_fee"] = os.getenv("TRADING212_CONVERSION_FEE_ACCOUNT")
        if os.getenv("TRADING212_FRENCH_TAX_ACCOUNT"):
            expense_accounts["french_tax"] = os.getenv("TRADING212_FRENCH_TAX_ACCOUNT")
        if os.getenv("TRADING212_STAMP_DUTY_ACCOUNT"):
            expense_accounts["stamp_duty_tax"] = os.getenv("TRADING212_STAMP_DUTY_ACCOUNT")
            
        if expense_accounts:
            config_data["expense_accounts"] = expense_accounts
        
        return cls(**config_data)
    
    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for YAML serialization
        data = self.dict()
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def get_gnucash_ticker(self, trading212_ticker: str) -> str:
        """Get GnuCash stock symbol for Trading 212 ticker, with fallback."""
        return self.ticker_map.get(trading212_ticker, trading212_ticker)
    
    # Deprecated alias for backward compatibility
    def get_yahoo_ticker(self, trading212_ticker: str) -> str:
        """Deprecated: Use get_gnucash_ticker instead."""
        return self.get_gnucash_ticker(trading212_ticker)
    
    def get_tax_account(self, tax_type: str) -> str:
        """Get the appropriate tax account based on tax type."""
        if tax_type == "french":
            return self.expense_accounts.french_tax
        elif tax_type == "stamp_duty":
            return self.expense_accounts.stamp_duty_tax
        else:
            # Default to French tax account for unknown types
            return self.expense_accounts.french_tax


def create_sample_config(config_path: Union[str, Path]) -> None:
    """Create a sample configuration file."""
    config_path = Path(config_path)
    
    sample_config = Config()  # Use defaults
    
    # Add some example ticker mappings
    sample_config.ticker_map.update({
        "TSLA": "TSLA",
        "AMZN": "AMZN", 
        "NFLX": "NFLX",
        "META": "META",
        "NVDA": "NVDA",
        "FAKE": "FAKE.L"  # Example made-up company
    })
    
    sample_config.save_to_file(config_path)
    
    # Add comments to the generated file
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    commented_content = f"""# Trading 212 to GnuCash Multi-Split Converter Configuration
# Edit this file to customize your ticker symbols and account mappings

{content}
# 
# Configuration Notes:
# - ticker_map: Maps Trading 212 symbols to GnuCash stock symbols (may include exchange suffixes)
# - expense_accounts: GnuCash accounts for fees and taxes
# - deposit_account: Account for Trading 212 deposits
# - interest_account: Account for interest payments
# 
# The source account (bank/cash account) is configured during GnuCash import.
"""
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(commented_content)
