"""Data models for Trading 212 transactions and GnuCash output.

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

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Trading212Transaction(BaseModel):
    """Model for a Trading 212 CSV transaction row."""

    action: str = Field(
        ...,
        alias="Action",
        description="Transaction type (Market buy, Market sell, etc.)",
    )
    time: str = Field(..., alias="Time", description="Transaction timestamp")
    isin: Optional[str] = Field(
        None, alias="ISIN", description="International Securities Identification Number"
    )
    ticker: Optional[str] = Field(
        None, alias="Ticker", description="Stock ticker symbol"
    )
    name: Optional[str] = Field(None, alias="Name", description="Full company name")
    notes: Optional[str] = Field(None, alias="Notes", description="Additional notes")
    id: str = Field(..., alias="ID", description="Transaction ID")
    num_shares: Optional[Decimal] = Field(
        None, alias="No. of shares", description="Number of shares traded"
    )
    price_per_share: Optional[Decimal] = Field(
        None, alias="Price / share", description="Price per share"
    )
    price_currency: Optional[str] = Field(
        None, alias="Currency (Price / share)", description="Currency of share price"
    )
    exchange_rate: Optional[Decimal] = Field(
        None, alias="Exchange rate", description="Exchange rate used"
    )
    result_currency: Optional[str] = Field(
        None, alias="Currency (Result)", description="Result currency"
    )
    total: Decimal = Field(..., alias="Total", description="Total transaction amount")
    total_currency: str = Field(
        ..., alias="Currency (Total)", description="Currency of total amount"
    )
    conversion_fee: Optional[Decimal] = Field(
        None, alias="Currency conversion fee", description="Conversion fee"
    )
    conversion_fee_currency: Optional[str] = Field(
        None,
        alias="Currency (Currency conversion fee)",
        description="Conversion fee currency",
    )
    french_tax: Optional[Decimal] = Field(
        None, alias="French transaction tax", description="French transaction tax"
    )
    french_tax_currency: Optional[str] = Field(
        None,
        alias="Currency (French transaction tax)",
        description="French tax currency",
    )
    stamp_duty_tax: Optional[Decimal] = Field(
        None, alias="Stamp duty reserve tax", description="Stamp duty reserve tax"
    )
    stamp_duty_tax_currency: Optional[str] = Field(
        None,
        alias="Currency (Stamp duty reserve tax)",
        description="Stamp duty tax currency",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v):
        """Validate that action is one of the supported types."""
        supported_actions = [
            "Market buy",
            "Market sell",
            "Limit buy",
            "Limit sell",
            "Deposit",
            "Interest on cash",
        ]
        if v not in supported_actions:
            raise ValueError(
                f"Unsupported action type: {v}. Supported: {supported_actions}"
            )
        return v

    @field_validator(
        "num_shares",
        "price_per_share",
        "exchange_rate",
        "total",
        "conversion_fee",
        "french_tax",
        "stamp_duty_tax",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v):
        """Parse decimal values, handling empty strings."""
        if v == "" or v is None:
            return None
        try:
            return Decimal(str(v))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid decimal value: {v}")

    @field_validator(
        "isin",
        "ticker",
        "name",
        "notes",
        "price_currency",
        "result_currency",
        "total_currency",
        "conversion_fee_currency",
        "french_tax_currency",
        "stamp_duty_tax_currency",
        mode="before",
    )
    @classmethod
    def parse_string(cls, v):
        """Parse string values, handling None and empty strings."""
        if v is None or v == "":
            return None
        return str(v).strip() if v else None

    def is_trading_action(self) -> bool:
        """Check if this is a trading action (buy/sell)."""
        return self.action in ["Market buy", "Market sell", "Limit buy", "Limit sell"]

    def is_buy_action(self) -> bool:
        """Check if this is a buy action."""
        return self.action in ["Market buy", "Limit buy"]

    def is_sell_action(self) -> bool:
        """Check if this is a sell action."""
        return self.action in ["Market sell", "Limit sell"]

    def get_transaction_tax(self) -> Optional[Decimal]:
        """Get the transaction tax amount (French or Stamp Duty)."""
        if self.french_tax and self.french_tax != 0:
            return self.french_tax
        elif self.stamp_duty_tax and self.stamp_duty_tax != 0:
            return self.stamp_duty_tax
        return None

    def get_tax_type(self) -> Optional[str]:
        """Get the type of transaction tax."""
        if self.french_tax and self.french_tax != 0:
            return "french"
        elif self.stamp_duty_tax and self.stamp_duty_tax != 0:
            return "stamp_duty"
        return None


class GnuCashSplit(BaseModel):
    """Model for a GnuCash multi-split transaction row."""

    date: str = Field(..., description="Transaction date")
    number: str = Field(default="", description="Transaction number/ID")
    description: str = Field(..., description="Transaction description")
    memo: str = Field(default="", description="Split memo")
    account: str = Field(..., description="Account for this split")
    transaction_commodity: str = Field(
        default="", description="Transaction commodity (stock symbol)"
    )
    amount: str = Field(default="", description="Amount (for shares)")
    value: str = Field(..., description="Value in base currency")

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV writing."""
        return {
            "Date": self.date,
            "Number": self.number,
            "Description": self.description,
            "Memo": self.memo,
            "Account": self.account,
            "Transaction Commodity": self.transaction_commodity,
            "Amount": self.amount,
            "Value": self.value,
        }


class ConversionResult(BaseModel):
    """Result of converting a Trading 212 transaction to GnuCash splits."""

    splits: list[GnuCashSplit] = Field(..., description="List of GnuCash splits")
    warnings: list[str] = Field(default_factory=list, description="Conversion warnings")
    errors: list[str] = Field(default_factory=list, description="Conversion errors")

    @property
    def success(self) -> bool:
        """Check if conversion was successful (no errors)."""
        return len(self.errors) == 0
