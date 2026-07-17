"""Multiple BOM database support for legacy CoreUI compatibility.

This module provides support for reading and writing CAR files with
multiple specialized BOM databases, as used in older CoreUI versions.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
from .bom import BOMStore, BOMError
import struct


class MultiDatabaseCAR:
    """CAR file with multiple BOM databases.
    
    Older CoreUI versions (< 700) use a single BOMStore, while newer
    versions (700+) may use multiple specialized databases:
    - imagedb: Image renditions
    - colordb: Color definitions
    - fontdb: Font definitions
    - fontsizedb: Font size definitions
    - appearancedb: Appearance definitions
    - facetKeysdb: Facet keys (theme identifiers)
    - bitmapKeydb: Bitmap keys
    - zcbezeldb: Zero-code bezel database
    - zcglyphdb: Zero-code glyph database
    """
    
    def __init__(self, coreui_version: int = 975):
        self.coreui_version = coreui_version
        self.databases: Dict[str, BOMStore] = {}
        self.main_store: Optional[BOMStore] = None
        
        # Determine which databases to use based on version
        if coreui_version >= 700:
            self.database_names = [
                'imagedb', 'colordb', 'fontdb', 'fontsizedb',
                'appearancedb', 'facetKeysdb', 'bitmapKeydb'
            ]
            if coreui_version >= 850:
                self.database_names.extend(['zcbezeldb', 'zcglyphdb'])
        else:
            # Single database for old versions
            self.database_names = []
    
    @classmethod
    def from_path(cls, path: Path, coreui_version: int = 975) -> 'MultiDatabaseCAR':
        """Load a CAR file with multiple databases."""
        car = cls(coreui_version)
        
        # Load main BOMStore
        car.main_store = BOMStore.from_path(path)
        
        # Check for additional databases
        for db_name in car.database_names:
            try:
                # Try to load as separate database
                db_path = path.parent / f"{path.stem}_{db_name}{path.suffix}"
                if db_path.exists():
                    car.databases[db_name] = BOMStore.from_path(db_path)
            except Exception:
                # Database not found or invalid, skip
                pass
        
        return car
    
    def get_database(self, name: str) -> Optional[BOMStore]:
        """Get a specific database by name."""
        return self.databases.get(name)
    
    def has_database(self, name: str) -> bool:
        """Check if a database exists."""
        return name in self.databases
    
    def get_all_databases(self) -> Dict[str, BOMStore]:
        """Get all databases."""
        return self.databases.copy()
    
    def get_image_renditions(self) -> List[dict]:
        """Get all image renditions from imagedb or main store."""
        if self.has_database('imagedb'):
            store = self.databases['imagedb']
        else:
            store = self.main_store
        
        if store is None:
            return []
        
        # Extract renditions from RENDITIONS tree
        renditions = []
        try:
            if 'RENDITIONS' in store.variables:
                # Parse renditions (simplified)
                renditions_data = store.named_block('RENDITIONS')
                # TODO: Parse actual rendition data
                pass
        except BOMError:
            pass
        
        return renditions
    
    def get_color_definitions(self) -> Dict[str, dict]:
        """Get all color definitions from colordb or main store."""
        if self.has_database('colordb'):
            store = self.databases['colordb']
        else:
            store = self.main_store
        
        if store is None:
            return {}
        
        colors = {}
        try:
            if 'COLORDEFINITIONS' in store.variables:
                # Parse color definitions (simplified)
                color_data = store.named_block('COLORDEFINITIONS')
                # TODO: Parse actual color data
                pass
        except BOMError:
            pass
        
        return colors
    
    def get_facet_keys(self) -> Dict[str, int]:
        """Get all facet keys from facetKeysdb or main store."""
        if self.has_database('facetKeysdb'):
            store = self.databases['facetKeysdb']
        else:
            store = self.main_store
        
        if store is None:
            return {}
        
        facet_keys = {}
        try:
            if 'FACETKEYS' in store.variables:
                # Parse facet keys (simplified)
                facet_data = store.named_block('FACETKEYS')
                # TODO: Parse actual facet key data
                pass
        except BOMError:
            pass
        
        return facet_keys
    
    def write_multi_database_car(self, output_path: Path, renditions: List[dict], 
                                 colors: Dict[str, dict], facet_keys: Dict[str, int]):
        """Write a CAR file with multiple databases.
        
        For CoreUI >= 700, creates separate database files.
        For CoreUI < 700, creates a single BOMStore.
        """
        if self.coreui_version >= 700 and len(self.database_names) > 0:
            # Write separate databases
            for db_name in self.database_names:
                db_path = output_path.parent / f"{output_path.stem}_{db_name}{output_path.suffix}"
                # TODO: Implement actual database writing
                pass
        else:
            # Write single database
            # TODO: Implement single database writing
            pass
    
    def validate_compatibility(self) -> Tuple[bool, str]:
        """Validate that the CAR file is compatible with the CoreUI version."""
        # Check database requirements
        if self.coreui_version >= 700:
            required_dbs = ['imagedb', 'colordb', 'facetKeysdb']
            for db_name in required_dbs:
                if not self.has_database(db_name) and self.main_store is None:
                    return False, f"Missing required database: {db_name}"
        
        if self.coreui_version >= 850:
            optional_dbs = ['zcbezeldb', 'zcglyphdb']
            # These are optional, just warn if missing
            for db_name in optional_dbs:
                if not self.has_database(db_name):
                    pass  # Optional, no error
        
        return True, ""
