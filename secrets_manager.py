"""
Secure secret management for Cascade REST CLI
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
import getpass

try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    import subprocess
    import json as json_module

    ONEPASSWORD_AVAILABLE = True
except ImportError:
    ONEPASSWORD_AVAILABLE = False

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import DEFAULT_CMS_PATH
from logging_config import logger


class SecretsManager:
    """Secure management of API keys, passwords, and connection details"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".cascade_cli"
        self.config_dir.mkdir(exist_ok=True)

        self.secrets_file = self.config_dir / "secrets.json"
        self.key_file = self.config_dir / ".key"

        # Initialize encryption
        self._setup_encryption()

    def _setup_encryption(self):
        """Setup encryption key for secure storage"""
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.encryption_key = f.read()
        else:
            # Generate new encryption key
            self.encryption_key = Fernet.generate_key()
            with open(self.key_file, "w") as f:
                # Store key with restricted permissions
                os.chmod(self.key_file, 0o600)
                with open(self.key_file, "wb") as f:
                    f.write(self.encryption_key)

        self.cipher = Fernet(self.encryption_key)

    def store_connection(
        self,
        connection_name: str,
        cms_path: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_keyring: bool = True,
    ) -> bool:
        """Store connection details securely"""

        connection_data = {
            "cms_path": cms_path,
            "created": self._get_timestamp(),
            "auth_type": None,
        }

        # Store authentication details
        if api_key:
            if use_keyring and KEYRING_AVAILABLE:
                keyring.set_password(
                    "cascade_cli", f"{connection_name}_api_key", api_key
                )
                connection_data["auth_type"] = "api_key_keyring"
            else:
                connection_data["api_key"] = self._encrypt(api_key)
                connection_data["auth_type"] = "api_key_encrypted"

        elif username and password:
            if use_keyring and KEYRING_AVAILABLE:
                keyring.set_password(
                    "cascade_cli", f"{connection_name}_username", username
                )
                keyring.set_password(
                    "cascade_cli", f"{connection_name}_password", password
                )
                connection_data["auth_type"] = "username_password_keyring"
            else:
                connection_data["username"] = username
                connection_data["password"] = self._encrypt(password)
                connection_data["auth_type"] = "username_password_encrypted"

        # Store connection data
        connections = self._load_connections()
        connections[connection_name] = connection_data
        self._save_connections(connections)

        logger.log_operation_end(
            "store_connection",
            True,
            connection_name=connection_name,
            auth_type=connection_data["auth_type"],
        )

        return True

    def get_connection(self, connection_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored connection details"""

        connections = self._load_connections()
        if connection_name not in connections:
            return None

        connection_data = connections[connection_name].copy()

        # Decrypt or retrieve from keyring
        if connection_data["auth_type"] == "api_key_encrypted":
            connection_data["api_key"] = self._decrypt(connection_data["api_key"])

        elif connection_data["auth_type"] == "username_password_encrypted":
            connection_data["password"] = self._decrypt(connection_data["password"])

        elif connection_data["auth_type"] == "api_key_keyring" and KEYRING_AVAILABLE:
            connection_data["api_key"] = keyring.get_password(
                "cascade_cli", f"{connection_name}_api_key"
            )

        elif (
            connection_data["auth_type"] == "username_password_keyring"
            and KEYRING_AVAILABLE
        ):
            connection_data["username"] = keyring.get_password(
                "cascade_cli", f"{connection_name}_username"
            )
            connection_data["password"] = keyring.get_password(
                "cascade_cli", f"{connection_name}_password"
            )

        logger.log_operation_end(
            "get_connection", True, connection_name=connection_name
        )
        return connection_data

    def list_connections(self) -> Dict[str, Dict[str, Any]]:
        """List all stored connections (without sensitive data)"""

        connections = self._load_connections()
        safe_connections = {}

        for name, data in connections.items():
            safe_connections[name] = {
                "cms_path": data["cms_path"],
                "auth_type": data["auth_type"],
                "created": data["created"],
            }

        return safe_connections

    def delete_connection(self, connection_name: str) -> bool:
        """Delete stored connection and cleanup keyring entries"""

        connections = self._load_connections()
        if connection_name not in connections:
            return False

        connection_data = connections[connection_name]

        # Cleanup keyring entries
        if KEYRING_AVAILABLE:
            if connection_data["auth_type"] == "api_key_keyring":
                keyring.delete_password("cascade_cli", f"{connection_name}_api_key")
            elif connection_data["auth_type"] == "username_password_keyring":
                keyring.delete_password("cascade_cli", f"{connection_name}_username")
                keyring.delete_password("cascade_cli", f"{connection_name}_password")

        # Remove from connections
        del connections[connection_name]
        self._save_connections(connections)

        logger.log_operation_end(
            "delete_connection", True, connection_name=connection_name
        )
        return True

    def get_from_environment(self) -> Optional[Dict[str, Any]]:
        """Get connection details from environment variables"""

        env_vars = {
            "CASCADE_API_KEY": os.getenv("CASCADE_API_KEY"),
            "CASCADE_USERNAME": os.getenv("CASCADE_USERNAME"),
            "CASCADE_PASSWORD": os.getenv("CASCADE_PASSWORD"),
            "CASCADE_URL": os.getenv("CASCADE_URL", DEFAULT_CMS_PATH),
        }

        # Check if we have at least API key or username/password
        if env_vars["CASCADE_API_KEY"] or (
            env_vars["CASCADE_USERNAME"] and env_vars["CASCADE_PASSWORD"]
        ):
            return {
                "cms_path": env_vars["CASCADE_URL"],
                "api_key": env_vars["CASCADE_API_KEY"],
                "username": env_vars["CASCADE_USERNAME"],
                "password": env_vars["CASCADE_PASSWORD"],
                "source": "environment",
            }

        return None

    def get_from_1password(self, vault: str, item: str) -> Optional[Dict[str, Any]]:
        """Get connection details from 1Password"""

        if not ONEPASSWORD_AVAILABLE:
            logger.log_error(
                Exception("1Password CLI not available"),
                {"operation": "get_from_1password"},
            )
            return None

        try:
            # Check if 1Password CLI is authenticated
            result = subprocess.run(
                ["op", "account", "list", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                logger.log_error(
                    Exception("1Password CLI not authenticated"),
                    {"operation": "get_from_1password"},
                )
                return None

            # Get item details from 1Password
            result = subprocess.run(
                ["op", "item", "get", item, "--vault", vault, "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )

            item_data = json_module.loads(result.stdout)

            # Extract fields from 1Password item
            fields = {}
            for field in item_data.get("fields", []):
                if "value" in field:
                    fields[field["label"].lower()] = field["value"]

            # Look for common field names
            cms_path = (
                fields.get("url")
                or fields.get("cascade url")
                or fields.get("cms path")
                or fields.get("server url")
                or fields.get("hostname")
                or DEFAULT_CMS_PATH
            )

            api_key = (
                fields.get("api key")
                or fields.get("api_key")
                or fields.get("token")
                or fields.get("credential")  # 1Password API credential field
                or fields.get(
                    "password"
                )  # Sometimes API keys are stored in password field
            )

            username = fields.get("username") or fields.get("user")
            password = fields.get("password") if not api_key else None

            # Validate we have authentication
            if not (api_key or (username and password)):
                logger.log_error(
                    Exception("No valid authentication found in 1Password item"),
                    {"operation": "get_from_1password", "item": item, "vault": vault},
                )
                return None

            logger.log_operation_end("get_from_1password", True, item=item, vault=vault)

            return {
                "cms_path": cms_path,
                "api_key": api_key,
                "username": username,
                "password": password,
                "source": "1password",
                "vault": vault,
                "item": item,
            }

        except subprocess.CalledProcessError as e:
            logger.log_error(
                e,
                {
                    "operation": "get_from_1password",
                    "item": item,
                    "vault": vault,
                    "error": e.stderr,
                },
            )
            return None
        except Exception as e:
            logger.log_error(
                e, {"operation": "get_from_1password", "item": item, "vault": vault}
            )
            return None

    def store_in_1password(
        self, vault: str, item_name: str, connection_data: Dict[str, Any]
    ) -> bool:
        """Store connection details in 1Password"""

        if not ONEPASSWORD_AVAILABLE:
            logger.log_error(
                Exception("1Password CLI not available"),
                {"operation": "store_in_1password"},
            )
            return False

        try:
            # Create item template for 1Password
            fields = [
                {"label": "URL", "value": connection_data["cms_path"], "type": "URL"},
            ]

            if connection_data.get("api_key"):
                fields.append(
                    {
                        "label": "API Key",
                        "value": connection_data["api_key"],
                        "type": "CONCEALED",
                    }
                )
            else:
                if connection_data.get("username"):
                    fields.append(
                        {
                            "label": "Username",
                            "value": connection_data["username"],
                            "type": "STRING",
                        }
                    )
                if connection_data.get("password"):
                    fields.append(
                        {
                            "label": "Password",
                            "value": connection_data["password"],
                            "type": "CONCEALED",
                        }
                    )

            item_template = {
                "title": item_name,
                "category": "API_CREDENTIAL",
                "fields": fields,
                "notesPlain": f"Cascade CMS connection for {item_name}\nCreated: {connection_data.get('created', 'unknown')}",
            }

            # Create or update item in 1Password
            result = subprocess.run(
                [
                    "op",
                    "item",
                    "create",
                    json_module.dumps(item_template),
                    "--vault",
                    vault,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.log_operation_end(
                "store_in_1password", True, item_name=item_name, vault=vault
            )
            return True

        except subprocess.CalledProcessError as e:
            logger.log_error(
                e,
                {
                    "operation": "store_in_1password",
                    "item_name": item_name,
                    "vault": vault,
                    "error": e.stderr,
                },
            )
            return False
        except Exception as e:
            logger.log_error(
                e,
                {
                    "operation": "store_in_1password",
                    "item_name": item_name,
                    "vault": vault,
                },
            )
            return False

    def list_1password_items(self, vault: str) -> List[Dict[str, Any]]:
        """List Cascade-related items in a 1Password vault"""

        if not ONEPASSWORD_AVAILABLE:
            return []

        try:
            result = subprocess.run(
                ["op", "item", "list", "--vault", vault, "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )

            items = json_module.loads(result.stdout)

            # Filter for Cascade-related items
            cascade_items = []
            for item in items:
                title = item.get("title", "").lower()
                if any(keyword in title for keyword in ["cascade", "cms", "api"]):
                    cascade_items.append(
                        {
                            "id": item["id"],
                            "title": item["title"],
                            "vault": vault,
                            "updated": item.get("updatedAt", ""),
                        }
                    )

            return cascade_items

        except Exception as e:
            logger.log_error(e, {"operation": "list_1password_items", "vault": vault})
            return []

    def interactive_setup(self, connection_name: str = "default") -> bool:
        """Interactive setup for storing connection details"""

        print(f"\n🔐 Setting up connection: {connection_name}")
        print("=" * 50)

        # Get CMS URL
        import click

        cms_path = click.prompt(
            "Cascade Server URL", default=DEFAULT_CMS_PATH, show_default=True
        )

        # Get authentication type
        auth_type = click.prompt(
            "Authentication type",
            type=click.Choice(["api_key", "username_password", "environment"]),
            default="api_key",
        )

        api_key = None
        username = None
        password = None

        if auth_type == "api_key":
            api_key = getpass.getpass("Enter API key: ")
            if not api_key:
                print("❌ API key is required")
                return False

        elif auth_type == "username_password":
            import click

            username = click.prompt("Username")
            password = getpass.getpass("Password: ")
            if not username or not password:
                print("❌ Username and password are required")
                return False

        elif auth_type == "environment":
            print("💡 Make sure to set these environment variables:")
            print("   export CASCADE_API_KEY='your_api_key'")
            print("   export CASCADE_USERNAME='your_username'")
            print("   export CASCADE_PASSWORD='your_password'")
            print("   export CASCADE_URL='https://your-cascade-server.com'")
            return True

        # Ask about keyring usage
        use_keyring = False
        if KEYRING_AVAILABLE:
            use_keyring = click.confirm(
                "Use system keyring for secure storage?", default=True
            )

        # Store the connection
        success = self.store_connection(
            connection_name, cms_path, api_key, username, password, use_keyring
        )

        if success:
            print(f"✅ Connection '{connection_name}' stored successfully")
            if use_keyring:
                print("🔒 Credentials stored in system keyring")
            else:
                print("🔒 Credentials encrypted and stored locally")
        else:
            print("❌ Failed to store connection")

        return success

    def _load_connections(self) -> Dict[str, Any]:
        """Load connections from file"""
        if not self.secrets_file.exists():
            return {}

        try:
            with open(self.secrets_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.log_error(e, {"operation": "load_connections"})
            return {}

    def _save_connections(self, connections: Dict[str, Any]):
        """Save connections to file"""
        try:
            with open(self.secrets_file, "w") as f:
                json.dump(connections, f, indent=2)
            # Restrict file permissions
            os.chmod(self.secrets_file, 0o600)
        except Exception as e:
            logger.log_error(e, {"operation": "save_connections"})

    def _encrypt(self, text: str) -> str:
        """Encrypt text for storage"""
        return self.cipher.encrypt(text.encode()).decode()

    def _decrypt(self, encrypted_text: str) -> str:
        """Decrypt text from storage"""
        return self.cipher.decrypt(encrypted_text.encode()).decode()

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.now().isoformat()


# Global secrets manager instance
secrets_manager = SecretsManager()
