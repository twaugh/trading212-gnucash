"""Trading 212 to GnuCash Converter.

A modern Python tool to convert Trading 212 CSV exports into a format suitable for GnuCash import.

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

__version__ = "2.0.0"
__author__ = "Tim Waugh"
__email__ = "twaugh@redhat.com"

from .config import Config
from .converter import Trading212Converter

__all__ = ["Trading212Converter", "Config"]
