"""
Database module for tracking migrated assets.
Uses SQLite to store mappings between source paths and Cascade asset IDs.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime


class MigrationDatabase:
    """
    SQLite database for tracking migration progress.
    Stores source path -> Cascade ID mappings for folders and pages.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. 
                     Defaults to ~/.cascade_cli/migration.db
        """
        if db_path is None:
            # Default to user's home directory
            home = Path.home()
            db_dir = home / '.cascade_cli'
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / 'migration.db')
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Folders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                source_path TEXT PRIMARY KEY,
                cascade_id TEXT NOT NULL,
                parent_path TEXT,
                folder_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Pages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                source_path TEXT PRIMARY KEY,
                cascade_id TEXT NOT NULL,
                folder_path TEXT,
                page_name TEXT NOT NULL,
                xml_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Links table (for symlink assets)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                source_key TEXT PRIMARY KEY,          -- e.g., 'link-assets/{folder}/{link_name}'
                cascade_id TEXT NOT NULL,             -- Cascade asset ID
                folder_name TEXT NOT NULL,            -- Domain folder name
                link_name TEXT NOT NULL,              -- Symlink asset name
                url TEXT,                             -- Target URL
                title TEXT,                           -- Optional display title
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_folders_cascade_id 
            ON folders(cascade_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_folders_parent 
            ON folders(parent_path)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pages_cascade_id 
            ON pages(cascade_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pages_folder 
            ON pages(folder_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_links_cascade_id
            ON links(cascade_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_links_folder
            ON links(folder_name)
        """)
        
        self.conn.commit()
    
    def add_folder(self, source_path: str, cascade_id: str, 
                   parent_path: str = None, folder_name: str = None) -> bool:
        """
        Add or update a folder in the database.
        
        Args:
            source_path: Relative path from source directory (e.g., "about/diversity")
            cascade_id: Cascade asset ID
            parent_path: Parent folder's source path
            folder_name: Name of the folder
            
        Returns:
            True if successful
        """
        if folder_name is None:
            folder_name = Path(source_path).name
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO folders 
            (source_path, cascade_id, parent_path, folder_name, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (source_path, cascade_id, parent_path, folder_name, datetime.now().isoformat()))
        
        self.conn.commit()
        return True
    
    def add_page(self, source_path: str, cascade_id: str,
                 folder_path: str = None, page_name: str = None,
                 xml_source: str = None) -> bool:
        """
        Add or update a page in the database.
        
        Args:
            source_path: Relative path from source directory (e.g., "about/index.xml")
            cascade_id: Cascade asset ID
            folder_path: Parent folder's source path
            page_name: Name of the page (without .xml)
            xml_source: Full path to source XML file
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO pages 
            (source_path, cascade_id, folder_path, page_name, xml_source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source_path, cascade_id, folder_path, page_name, xml_source, datetime.now().isoformat()))
        
        self.conn.commit()
        return True

    def add_link(self, source_key: str, cascade_id: str,
                 folder_name: str, link_name: str,
                 url: Optional[str] = None, title: Optional[str] = None) -> bool:
        """Add or update a symlink asset record."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO links
            (source_key, cascade_id, folder_name, link_name, url, title, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_key, cascade_id, folder_name, link_name, url, title, datetime.now().isoformat()),
        )
        self.conn.commit()
        return True

    def get_link_id(self, source_key: str) -> Optional[str]:
        """Get Cascade ID for a symlink by its source key."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT cascade_id FROM links WHERE source_key = ?",
            (source_key,),
        )
        row = cursor.fetchone()
        return row['cascade_id'] if row else None

    def link_exists(self, source_key: str) -> bool:
        return self.get_link_id(source_key) is not None
    
    def get_folder_id(self, source_path: str) -> Optional[str]:
        """
        Get Cascade ID for a folder by its source path.
        
        Args:
            source_path: Relative path from source directory
            
        Returns:
            Cascade ID or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT cascade_id FROM folders WHERE source_path = ?",
            (source_path,)
        )
        row = cursor.fetchone()
        return row['cascade_id'] if row else None
    
    def get_page_id(self, source_path: str) -> Optional[str]:
        """
        Get Cascade ID for a page by its source path.
        
        Args:
            source_path: Relative path from source directory
            
        Returns:
            Cascade ID or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT cascade_id FROM pages WHERE source_path = ?",
            (source_path,)
        )
        row = cursor.fetchone()
        return row['cascade_id'] if row else None
    
    def folder_exists(self, source_path: str) -> bool:
        """Check if a folder has been migrated."""
        return self.get_folder_id(source_path) is not None
    
    def page_exists(self, source_path: str) -> bool:
        """Check if a page has been migrated."""
        return self.get_page_id(source_path) is not None
    
    def get_all_folders(self) -> List[Dict[str, str]]:
        """Get all migrated folders."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM folders ORDER BY source_path")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_pages(self) -> List[Dict[str, str]]:
        """Get all migrated pages."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM pages ORDER BY source_path")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_folders_in_path(self, path_prefix: str) -> List[Dict[str, str]]:
        """Get all folders under a specific path."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM folders WHERE source_path LIKE ? ORDER BY source_path",
            (f"{path_prefix}%",)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_pages_in_folder(self, folder_path: str) -> List[Dict[str, str]]:
        """Get all pages in a specific folder."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM pages WHERE folder_path = ? ORDER BY page_name",
            (folder_path,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def build_folder_id_map(self) -> Dict[str, str]:
        """
        Build a complete folder path -> ID mapping from database.
        
        Returns:
            Dictionary mapping source paths to Cascade IDs
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT source_path, cascade_id FROM folders")
        
        folder_map = {}
        for row in cursor.fetchall():
            folder_map[row['source_path']] = row['cascade_id']
        
        return folder_map
    
    def get_stats(self) -> Dict[str, int]:
        """Get migration statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM folders")
        folder_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM pages")
        page_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM links")
        link_count = cursor.fetchone()['count']
        
        return {
            'folders': folder_count,
            'pages': page_count,
            'links': link_count,
            'total': folder_count + page_count + link_count
        }
    
    def clear_all(self):
        """Clear all data from the database. USE WITH CAUTION!"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM folders")
        cursor.execute("DELETE FROM pages")
        cursor.execute("DELETE FROM links")
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global database instance
_db_instance = None


def get_db() -> MigrationDatabase:
    """Get global database instance (singleton pattern)."""
    global _db_instance
    if _db_instance is None:
        _db_instance = MigrationDatabase()
    return _db_instance


if __name__ == "__main__":
    # Test the database
    with MigrationDatabase() as db:
        print("Database initialized at:", db.db_path)
        
        # Test adding data
        db.add_folder("test-folder", "test-id-123", None, "test-folder")
        db.add_page("test-folder/test-page.xml", "test-page-id", "test-folder", "test-page")
        
        # Test retrieval
        folder_id = db.get_folder_id("test-folder")
        page_id = db.get_page_id("test-folder/test-page.xml")
        
        print(f"Folder ID: {folder_id}")
        print(f"Page ID: {page_id}")
        
        # Test stats
        stats = db.get_stats()
        print(f"Stats: {stats}")
        
        print("\n✅ Database tests passed!")
