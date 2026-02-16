"""
Migration logging system with structured log levels.

Log Levels:
- ERROR: Failed operations (missing asset IDs, unmapped field groups, etc.)
- WARNING: Planned skips (display=Off, heading downgrades, image removals, stripped tags)
- INFO: Successful migrations with XPath context
"""

from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from xml.sax.saxutils import escape as xml_escape
import json
import os


class LogLevel(Enum):
    ERROR = 1
    WARNING = 2
    INFO = 3
    
    def __str__(self):
        return self.name


@dataclass
class LogEntry:
    """Single log entry with level, timestamp, and message."""
    level: LogLevel
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context: Optional[str] = None  # XPath or other context
    
    def format(self) -> str:
        """Format as [LEVEL] timestamp message"""
        ctx = f" ({self.context})" if self.context else ""
        return f"[{self.level}] {self.timestamp} {self.message}{ctx}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'level': str(self.level),
            'timestamp': self.timestamp,
            'message': self.message,
            'context': self.context
        }


class MigrationLogger:
    """
    Logger for migration operations.
    
    Collects log entries during migration and can output to:
    - Migration summary field (per-page, in destination XML)
    - Global log file (aggregates all pages)
    """
    
    def __init__(self, page_path: str = None, file_path: str = None):
        self.page_path = page_path      # CMS path (e.g., /student-life/career-services/internships)
        self.file_path = file_path      # Filesystem path (e.g., /Users/.../internships.xml)
        self.entries: List[LogEntry] = []
        self._global_log_file: Optional[str] = None
    
    def set_global_log_file(self, path: str):
        """Set path for global log file (used in batch operations)."""
        self._global_log_file = path
    
    def _add(self, level: LogLevel, message: str, context: str = None):
        """Add a log entry."""
        entry = LogEntry(level=level, message=message, context=context)
        self.entries.append(entry)
        return entry
    
    def error(self, message: str, context: str = None) -> LogEntry:
        """Log an ERROR - failed operations."""
        return self._add(LogLevel.ERROR, message, context)
    
    def warning(self, message: str, context: str = None) -> LogEntry:
        """Log a WARNING - planned skips, downgrades, removals."""
        return self._add(LogLevel.WARNING, message, context)
    
    def info(self, message: str, context: str = None) -> LogEntry:
        """Log INFO - successful migrations."""
        return self._add(LogLevel.INFO, message, context)
    
    def get_entries_by_level(self, level: LogLevel) -> List[LogEntry]:
        """Get all entries of a specific level."""
        return [e for e in self.entries if e.level == level]
    
    def get_sorted_entries(self) -> List[LogEntry]:
        """Get entries sorted by level (ERROR first, then WARNING, then INFO)."""
        return sorted(self.entries, key=lambda e: e.level.value)
    
    def has_errors(self) -> bool:
        """Check if any errors were logged."""
        return any(e.level == LogLevel.ERROR for e in self.entries)
    
    def get_stats(self) -> dict:
        """Get count of entries by level."""
        return {
            'errors': len(self.get_entries_by_level(LogLevel.ERROR)),
            'warnings': len(self.get_entries_by_level(LogLevel.WARNING)),
            'info': len(self.get_entries_by_level(LogLevel.INFO)),
            'total': len(self.entries)
        }
    
    def format_for_summary(self) -> str:
        """
        Format log entries for migration-summary field.
        Returns XHTML wrapped in <code> element with timestamp header.
        """
        if not self.entries:
            return "<code>No migration log entries.</code>"
        
        # Sort by level (errors first)
        sorted_entries = self.get_sorted_entries()
        
        # Format each entry (without individual timestamps)
        lines = []
        for entry in sorted_entries:
            ctx = f" ({entry.context})" if entry.context else ""
            line = f"[{entry.level}] {entry.message}{ctx}"
            lines.append(xml_escape(line))
        
        # Join with newlines, wrap in <code> with timestamp header
        timestamp = datetime.now(timezone.utc).isoformat()
        log_content = "\n".join(lines)
        return f"<code>{timestamp}\n{log_content}</code>"
    
    def write_to_global_log(self):
        """Append entries to global log file (JSONL format)."""
        if not self._global_log_file:
            return
        
        # Create directory if needed
        log_dir = os.path.dirname(self._global_log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Append as JSONL (one JSON object per line)
        with open(self._global_log_file, 'a', encoding='utf-8') as f:
            for entry in self.entries:
                record = {
                    'file_path': self.file_path,
                    'page_path': self.page_path,
                    **entry.to_dict()
                }
                f.write(json.dumps(record) + '\n')
    
    def clear(self):
        """Clear all entries."""
        self.entries = []


class GlobalMigrationLog:
    """
    Manages the global migration log file for batch operations.
    
    Provides methods to:
    - Initialize a new log file
    - Read and summarize existing logs
    - Generate reports
    """
    
    def __init__(self, log_path: str):
        self.log_path = log_path
    
    def initialize(self):
        """Initialize a new log file (clears existing)."""
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Write header comment
        with open(self.log_path, 'w', encoding='utf-8') as f:
            header = {
                'type': 'migration_log_header',
                'started': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
            f.write(json.dumps(header) + '\n')
    
    def read_entries(self) -> List[dict]:
        """Read all entries from log file."""
        entries = []
        if not os.path.exists(self.log_path):
            return entries
        
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if entry.get('type') != 'migration_log_header':
                            entries.append(entry)
                    except json.JSONDecodeError:
                        pass
        return entries
    
    def get_summary(self) -> dict:
        """Get summary statistics from log file."""
        entries = self.read_entries()
        
        files = set()
        pages = set()
        by_level = {'ERROR': 0, 'WARNING': 0, 'INFO': 0}
        errors_by_file = {}
        warnings_by_file = {}
        
        for entry in entries:
            file_path = entry.get('file_path', 'unknown')
            page_path = entry.get('page_path', 'unknown')
            files.add(file_path)
            pages.add(page_path)
            
            level = entry.get('level', 'INFO')
            by_level[level] = by_level.get(level, 0) + 1
            
            if level == 'ERROR':
                if file_path not in errors_by_file:
                    errors_by_file[file_path] = {'page_path': page_path, 'messages': []}
                errors_by_file[file_path]['messages'].append(entry.get('message', ''))
            elif level == 'WARNING':
                if file_path not in warnings_by_file:
                    warnings_by_file[file_path] = {'page_path': page_path, 'messages': []}
                warnings_by_file[file_path]['messages'].append(entry.get('message', ''))
        
        return {
            'total_files': len(files),
            'total_pages': len(pages),
            'total_entries': len(entries),
            'by_level': by_level,
            'files_with_errors': len(errors_by_file),
            'errors_by_file': errors_by_file,
            'files_with_warnings': len(warnings_by_file),
            'warnings_by_file': warnings_by_file
        }
    
    def write_error_log(self, error_log_path: str):
        """
        Write a focused log containing only ERROR and WARNING entries.
        Format: simple text, easy to review.
        """
        entries = self.read_entries()
        
        errors = [e for e in entries if e.get('level') == 'ERROR']
        warnings = [e for e in entries if e.get('level') == 'WARNING']
        
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"Migration Error Log - {datetime.now(timezone.utc).isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            
            if errors:
                f.write(f"ERRORS ({len(errors)})\n")
                f.write("-" * 40 + "\n")
                for e in errors:
                    f.write(f"{e.get('file_path', 'unknown')}\n")
                    f.write(f"  {e.get('message', '')}\n\n")
            else:
                f.write("No errors.\n\n")
            
            if warnings:
                f.write(f"\nWARNINGS ({len(warnings)})\n")
                f.write("-" * 40 + "\n")
                # Group warnings by file
                by_file = {}
                for w in warnings:
                    fp = w.get('file_path', 'unknown')
                    if fp not in by_file:
                        by_file[fp] = []
                    by_file[fp].append(w.get('message', ''))
                
                for fp, msgs in by_file.items():
                    f.write(f"{fp}\n")
                    for msg in msgs:
                        f.write(f"  - {msg}\n")
                    f.write("\n")
            else:
                f.write("No warnings.\n")
        
        return len(errors), len(warnings)
    
    def generate_report(self) -> str:
        """Generate a human-readable summary report."""
        summary = self.get_summary()
        
        lines = [
            "=" * 80,
            "MIGRATION LOG SUMMARY",
            "=" * 80,
            f"Total files processed: {summary['total_files']}",
            f"Total log entries: {summary['total_entries']}",
            "",
            "By Level:",
            f"  ERROR:   {summary['by_level']['ERROR']}",
            f"  WARNING: {summary['by_level']['WARNING']}",
            f"  INFO:    {summary['by_level']['INFO']}",
        ]
        
        if summary['files_with_errors'] > 0:
            lines.extend([
                "",
                "-" * 80,
                f"FILES WITH ERRORS ({summary['files_with_errors']})",
                "-" * 80,
            ])
            for file_path, data in summary['errors_by_file'].items():
                lines.append(f"\n  File: {file_path}")
                lines.append(f"  Page: {data['page_path']}")
                for err in data['messages'][:5]:  # Show first 5 errors per file
                    lines.append(f"    - {err[:100]}")
                if len(data['messages']) > 5:
                    lines.append(f"    ... and {len(data['messages']) - 5} more")
        
        if summary['files_with_warnings'] > 0:
            lines.extend([
                "",
                "-" * 80,
                f"FILES WITH WARNINGS ({summary['files_with_warnings']})",
                "-" * 80,
            ])
            for file_path, data in summary['warnings_by_file'].items():
                lines.append(f"\n  File: {file_path}")
                lines.append(f"  Page: {data['page_path']}")
                lines.append(f"    Warnings: {len(data['messages'])}")
        
        lines.append("\n" + "=" * 80)
        return "\n".join(lines)
