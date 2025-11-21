#!/usr/bin/env python3
"""
Session Manager for Cascade REST CLI

Handles persistent session storage so credentials persist between CLI commands.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import base64
from cryptography.fernet import Fernet

from secrets_manager import secrets_manager
from logging_config import logger


class SessionManager:
    """Manages persistent CLI sessions with encrypted credential storage"""
    
    def __init__(self, session_dir: Optional[Path] = None):
        self.session_dir = session_dir or Path.home() / ".cascade_cli" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_file = self.session_dir / "current_session.json"
        self.session_key_file = self.session_dir / ".session_key"
        
        # Initialize encryption
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Setup encryption for session storage"""
        if self.session_key_file.exists():
            with open(self.session_key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new encryption key
            self.encryption_key = Fernet.generate_key()
            with open(self.session_key_file, 'wb') as f:
                f.write(self.encryption_key)
            # Restrict permissions
            os.chmod(self.session_key_file, 0o600)
        
        self.cipher = Fernet(self.encryption_key)
    
    def create_session(
        self,
        cms_path: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        source: str = "manual"
    ) -> bool:
        """Create a new session with credentials"""
        
        session_data = {
            "cms_path": cms_path,
            "api_key": self._encrypt(api_key) if api_key else None,
            "username": self._encrypt(username) if username else None,
            "password": self._encrypt(password) if password else None,
            "source": source,
            "created": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            # Restrict permissions
            os.chmod(self.session_file, 0o600)
            
            logger.log_operation_end("create_session", True, 
                                   cms_path=cms_path, source=source)
            return True
            
        except Exception as e:
            logger.log_error(e, {"operation": "create_session"})
            return False
    
    def create_session_from_1password(self, vault: str, item: str) -> bool:
        """Create session from 1Password credentials"""
        
        connection_data = secrets_manager.get_from_1password(vault, item)
        
        if not connection_data:
            return False
        
        return self.create_session(
            connection_data["cms_path"],
            connection_data.get("api_key"),
            connection_data.get("username"),
            connection_data.get("password"),
            source=f"1password:{vault}:{item}"
        )
    
    def get_session(self) -> Optional[Dict[str, Any]]:
        """Get current session credentials"""
        
        if not self.session_file.exists():
            return None
        
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if session has expired
            expires = datetime.fromisoformat(session_data["expires"])
            if datetime.now() > expires:
                self.clear_session()
                return None
            
            # Decrypt credentials
            decrypted_data = {
                "cms_path": session_data["cms_path"],
                "api_key": self._decrypt(session_data["api_key"]) if session_data.get("api_key") else None,
                "username": self._decrypt(session_data["username"]) if session_data.get("username") else None,
                "password": self._decrypt(session_data["password"]) if session_data.get("password") else None,
                "source": session_data["source"],
                "created": session_data["created"],
                "expires": session_data["expires"]
            }
            
            return decrypted_data
            
        except Exception as e:
            logger.log_error(e, {"operation": "get_session"})
            return None
    
    def clear_session(self) -> bool:
        """Clear current session"""
        
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            
            logger.log_operation_end("clear_session", True)
            return True
            
        except Exception as e:
            logger.log_error(e, {"operation": "clear_session"})
            return False
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid"""
        
        session = self.get_session()
        return session is not None
    
    def extend_session(self, hours: int = 24) -> bool:
        """Extend current session expiration"""
        
        session = self.get_session()
        if not session:
            return False
        
        # Recreate session with extended expiration
        return self.create_session(
            session["cms_path"],
            session["api_key"],
            session["username"],
            session["password"],
            source=session["source"]
        )
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get session information (without credentials)"""
        
        session = self.get_session()
        if not session:
            return None
        
        return {
            "cms_path": session["cms_path"],
            "source": session["source"],
            "created": session["created"],
            "expires": session["expires"]
        }
    
    def _encrypt(self, text: str) -> str:
        """Encrypt text for storage"""
        return self.cipher.encrypt(text.encode()).decode()
    
    def _decrypt(self, encrypted_text: str) -> str:
        """Decrypt text from storage"""
        return self.cipher.decrypt(encrypted_text.encode()).decode()


# Global session manager instance
session_manager = SessionManager()
