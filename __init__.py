"""
CRUD Archive Package

Provides functionality for creating, reading, updating, and deleting .crudearch files.
Includes both programmatic access and a GUI manager.
"""

from .archive_handler import CrudeArchiveHandler
from .common import ArchiveCommon
from .manager import CrudeArchiveManager, run_gui

__all__ = ['CrudeArchiveHandler', 'ArchiveCommon', 'CrudeArchiveManager', 'run_gui']
__version__ = '1.0.0'
