#!/usr/bin/env python3
"""
Cascade REST CLI

Interactive command-line interface for Cascade Server REST API operations.
"""

import click
import getpass
import json
import asyncio
from typing import Optional, Dict, Any, List
import cascade_rest as cascade
from logging_config import logger
from rollback import rollback_manager
from csv_operations import csv_ops
from advanced_filtering import advanced_filter
from performance import performance_monitor, parallel_processor, cache_manager
from secrets_manager import secrets_manager
from test_environment_helpers import test_manager
from scheduled_jobs import job_scheduler, JobType, JobStatus
from session_manager import session_manager


class CascadeCLI:
    def __init__(self):
        self.auth = None
        self.cms_path = None
        self.connected = False
        self._auto_load_session()

    def setup_connection(
        self,
        cms_path: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Set up authentication and connection to Cascade Server"""
        self.cms_path = cms_path

        if api_key:
            self.auth = {"apiKey": api_key}
        elif username and password:
            self.auth = {"u": username, "p": password}
        else:
            # Interactive mode
            auth_type = click.prompt(
                "Authentication type",
                type=click.Choice(["api_key", "username_password"]),
                default="api_key",
            )

            if auth_type == "api_key":
                api_key = getpass.getpass("Enter API key: ")
                self.auth = {"apiKey": api_key}
            else:
                username = click.prompt("Username")
                password = getpass.getpass("Password: ")
                self.auth = {"u": username, "p": password}

        # Test connection
        try:
            sites = cascade.list_sites(self.cms_path, self.auth)
            self.connected = True
            click.echo(f"✅ Connected to {self.cms_path}")
            return True
        except Exception as e:
            click.echo(f"❌ Connection failed: {e}")
            return False

    def _auto_load_session(self):
        """Automatically load session credentials if available"""

        session = session_manager.get_session()
        if session:
            # Set credentials without testing connection to avoid output during auto-load
            self.cms_path = session["cms_path"]
            if session.get("api_key"):
                self.auth = {"apiKey": session["api_key"]}
            elif session.get("username") and session.get("password"):
                self.auth = {"u": session["username"], "p": session["password"]}

            # Test connection silently
            try:
                cascade.list_sites(self.cms_path, self.auth)
                self.connected = True
            except Exception:
                # Connection failed, reset credentials
                self.auth = None
                self.cms_path = None
                self.connected = False

    def read_asset(self, asset_type: str, asset_id: str) -> Optional[Dict[str, Any]]:
        """Read a single asset"""
        if not self.connected or not self.cms_path or not self.auth:
            click.echo("❌ Not connected. Use setup first.")
            return None

        try:
            result = cascade.read_single_asset(
                self.cms_path, self.auth, asset_type, asset_id
            )
            return result
        except Exception as e:
            click.echo(f"❌ Error reading asset: {e}")
            return None

    def search_assets(
        self, search_terms: str, site_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Search for assets"""
        if not self.connected or not self.cms_path or not self.auth:
            click.echo("❌ Not connected. Use setup first.")
            return None

        try:
            result = cascade.search_assets(
                self.cms_path, self.auth, search_terms, site_name=site_name
            )
            return result
        except Exception as e:
            click.echo(f"❌ Error searching assets: {e}")
            return None

    def get_folder_children(self, folder_id: str) -> Optional[list]:
        """Get children of a folder"""
        if not self.connected or not self.cms_path or not self.auth:
            click.echo("❌ Not connected. Use setup first.")
            return None

        try:
            result = cascade.get_folder_children(self.cms_path, self.auth, folder_id)
            return result
        except Exception as e:
            click.echo(f"❌ Error getting folder children: {e}")
            return None

    def update_metadata(
        self, asset_type: str, asset_id: str, field_name: str, new_value: str
    ) -> bool:
        """Update metadata field"""
        if not self.connected or not self.cms_path or not self.auth:
            click.echo("❌ Not connected. Use setup first.")
            return False

        try:
            result = cascade.set_single_asset_metadata_value(
                self.cms_path, self.auth, asset_type, asset_id, field_name, new_value
            )
            click.echo(f"✅ Updated {field_name} to '{new_value}'")
            return True
        except Exception as e:
            click.echo(f"❌ Error updating metadata: {e}")
            return False

    def publish_asset(
        self, asset_type: str, asset_id: str, unpublish: bool = False
    ) -> bool:
        """Publish or unpublish an asset"""
        if not self.connected or not self.cms_path or not self.auth:
            click.echo("❌ Not connected. Use setup first.")
            return False

        try:
            result = cascade.publish_asset(
                self.cms_path, self.auth, asset_type, asset_id, unpublish=unpublish
            )
            action = "Unpublished" if unpublish else "Published"
            click.echo(f"✅ {action} {asset_type} {asset_id}")
            return True
        except Exception as e:
            click.echo(f"❌ Error publishing asset: {e}")
            return False

    def batch_update_metadata(
        self,
        asset_type: str,
        path_pattern: str,
        field_name: str,
        new_value: str,
        site_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Batch update metadata for assets matching type and path pattern"""
        if not self.connected or not self.cms_path or not self.auth:
            click.echo("❌ Not connected. Use setup first.")
            return {"success": 0, "failed": 0, "skipped": 0}

        # Search for assets of the specified type
        search_query = f"type:{asset_type}"
        if site_name:
            search_query += f" site:{site_name}"

        click.echo(f"🔍 Searching for {asset_type} assets...")
        search_result = self.search_assets(search_query, site_name)

        if not search_result or "matches" not in search_result:
            click.echo("❌ No search results found")
            return {"success": 0, "failed": 0, "skipped": 0}

        # Filter assets by path pattern
        matching_assets = []
        for asset in search_result["matches"]:
            if "path" in asset and path_pattern.lower() in asset["path"].lower():
                matching_assets.append(asset)

        if not matching_assets:
            click.echo(
                f"❌ No {asset_type} assets found with path containing '{path_pattern}'"
            )
            return {"success": 0, "failed": 0, "skipped": 0}

        click.echo(f"📝 Found {len(matching_assets)} assets matching criteria")

        if dry_run:
            click.echo("🔍 DRY RUN - No changes will be made")
            for asset in matching_assets:
                click.echo(
                    f"  Would update: {asset['type']} {asset['id']} - {asset.get('path', 'N/A')}"
                )
            return {"success": 0, "failed": 0, "skipped": len(matching_assets)}

        # Update each matching asset
        results = {"success": 0, "failed": 0, "skipped": 0}

        with click.progressbar(matching_assets, label="Updating assets") as assets:
            for asset in assets:
                try:
                    success = self.update_metadata(
                        asset["type"], asset["id"], field_name, new_value
                    )
                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    click.echo(f"❌ Error updating {asset['type']} {asset['id']}: {e}")
                    results["failed"] += 1

        return results

    def batch_set_tag(
        self,
        asset_type: str,
        path_pattern: str,
        tag_name: str,
        site_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Set a tag on multiple assets matching a path filter"""
        if not self.connected or not self.cms_path or not self.auth:
            click.echo("❌ Not connected. Use setup first.")
            return {"success": 0, "failed": 0}
        
        from cascade_rest.search import search_assets
        from cascade_rest.tags import add_asset_tags
        
        # Search for assets matching the path filter
        search_result = search_assets(self.cms_path, self.auth, path_pattern, site_name, None, [asset_type])
        
        if not search_result.get("success"):
            click.echo(f"❌ Search failed: {search_result}")
            return {"success": 0, "failed": 0}
        
        assets = search_result.get("matches", [])
        if not assets:
            click.echo(f"❌ No {asset_type} assets found matching '{path_pattern}'")
            return {"success": 0, "failed": 0}
        
        click.echo(f"🔍 Found {len(assets)} {asset_type} assets matching '{path_pattern}'")
        
        if dry_run:
            click.echo("🧪 DRY RUN - Would set the following tags:")
            for asset in assets:
                click.echo(f"  {asset_type}/{asset['id']}: {tag_name}")
            return {"success": len(assets), "failed": 0}
        
        # Set the tag on each asset
        success_count = 0
        failed_count = 0
        for asset in assets:
            try:
                result = add_asset_tags(self.cms_path, self.auth, asset["id"], asset_type, [tag_name])
                if result.get("success"):
                    success_count += 1
                    click.echo(f"✅ Set tag '{tag_name}' on {asset_type}/{asset['id']}")
                else:
                    failed_count += 1
                    click.echo(f"❌ Failed to set tag on {asset_type}/{asset['id']}: {result}")
            except Exception as e:
                failed_count += 1
                click.echo(f"❌ Error setting tag on {asset_type}/{asset['id']}: {e}")
        
        click.echo(f"🎉 Successfully set tag '{tag_name}' on {success_count}/{len(assets)} assets")
        return {"success": success_count, "failed": failed_count}

    def batch_publish_assets(
        self,
        asset_type: str,
        path_pattern: str,
        unpublish: bool = False,
        site_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Batch publish/unpublish assets matching type and path pattern"""
        if not self.connected or not self.cms_path or not self.auth:
            click.echo("❌ Not connected. Use setup first.")
            return {"success": 0, "failed": 0, "skipped": 0}

        # Search for assets of the specified type
        search_query = f"type:{asset_type}"
        if site_name:
            search_query += f" site:{site_name}"

        click.echo(f"🔍 Searching for {asset_type} assets...")
        search_result = self.search_assets(search_query, site_name)

        if not search_result or "matches" not in search_result:
            click.echo("❌ No search results found")
            return {"success": 0, "failed": 0, "skipped": 0}

        # Filter assets by path pattern
        matching_assets = []
        for asset in search_result["matches"]:
            if "path" in asset and path_pattern.lower() in asset["path"].lower():
                matching_assets.append(asset)

        if not matching_assets:
            click.echo(
                f"❌ No {asset_type} assets found with path containing '{path_pattern}'"
            )
            return {"success": 0, "failed": 0, "skipped": 0}

        action = "unpublish" if unpublish else "publish"
        click.echo(f"📝 Found {len(matching_assets)} assets to {action}")

        if dry_run:
            click.echo("🔍 DRY RUN - No changes will be made")
            for asset in matching_assets:
                click.echo(
                    f"  Would {action}: {asset['type']} {asset['id']} - {asset.get('path', 'N/A')}"
                )
            return {"success": 0, "failed": 0, "skipped": len(matching_assets)}

        # Publish/unpublish each matching asset
        results = {"success": 0, "failed": 0, "skipped": 0}

        with click.progressbar(
            matching_assets, label=f"{action.capitalize()}ing assets"
        ) as assets:
            for asset in assets:
                try:
                    success = self.publish_asset(asset["type"], asset["id"], unpublish)
                    if success:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    click.echo(
                        f"❌ Error {action}ing {asset['type']} {asset['id']}: {e}"
                    )
                    results["failed"] += 1

        return results

    def show_reports(self):
        """Show operation reports"""
        summary = cascade.get_report_summary()
        click.echo("\n📊 Operation Summary:")
        for status, count in summary.items():
            if count > 0:
                click.echo(f"  {status}: {count}")


# Global CLI instance
cli = CascadeCLI()


@click.group()
def main():
    """Cascade REST CLI - Interactive command-line interface for Cascade Server"""
    pass


@main.command()
@click.option(
    "--cms-path", default="https://cms.example.edu:8443", help="Cascade Server URL"
)
@click.option("--api-key", help="API key for authentication")
@click.option("--username", help="Username for authentication")
@click.option("--password", help="Password for authentication")
@click.option("--connection-name", default="default", help="Name for this connection")
@click.option(
    "--use-keyring", is_flag=True, help="Use system keyring for secure storage"
)
@click.option(
    "--from-env", is_flag=True, help="Load credentials from environment variables"
)
def setup(
    cms_path: str,
    api_key: Optional[str],
    username: Optional[str],
    password: Optional[str],
    connection_name: str,
    use_keyring: bool,
    from_env: bool,
):
    """Set up connection to Cascade Server with secure credential storage"""

    if from_env:
        # Load from environment variables
        env_connection = secrets_manager.get_from_environment()
        if env_connection:
            click.echo("✅ Loaded credentials from environment variables")
            cli.setup_connection(
                env_connection["cms_path"],
                env_connection.get("api_key"),
                env_connection.get("username"),
                env_connection.get("password"),
            )
            click.echo("✅ Connection setup complete")
        else:
            click.echo("❌ No valid credentials found in environment variables")
            click.echo(
                "💡 Set CASCADE_API_KEY, CASCADE_USERNAME, CASCADE_PASSWORD, CASCADE_URL"
            )
    else:
        # Store credentials securely
        success = secrets_manager.store_connection(
            connection_name, cms_path, api_key, username, password, use_keyring
        )

        if success:
            click.echo(f"✅ Connection '{connection_name}' stored securely")
            if use_keyring:
                click.echo("🔒 Credentials stored in system keyring")
            else:
                click.echo("🔒 Credentials encrypted and stored locally")

            # Set up current session
            cli.setup_connection(cms_path, api_key, username, password)
            click.echo("✅ Connection setup complete")
        else:
            click.echo("❌ Failed to store connection")


@main.command()
@click.argument("asset_type")
@click.argument("asset_id")
def read(asset_type: str, asset_id: str):
    """Read a single asset"""
    result = cli.read_asset(asset_type, asset_id)
    if result:
        click.echo(json.dumps(result, indent=2))


@main.command()
@click.argument("search_terms")
@click.option("--site", help="Site name to limit search")
def search(search_terms: str, site: Optional[str]):
    """Search for assets"""
    result = cli.search_assets(search_terms, site)
    if result:
        click.echo(json.dumps(result, indent=2))


@main.command()
@click.argument("folder_id")
def ls(folder_id: str):
    """List children of a folder"""
    children = cli.get_folder_children(folder_id)
    if children:
        click.echo(f"Found {len(children)} children:")
        for child in children:
            click.echo(f"  {child['type']}: {child['name']} (ID: {child['id']})")


@main.command()
@click.argument("asset_type")
@click.argument("asset_id")
@click.argument("field_name")
@click.argument("new_value")
def update(asset_type: str, asset_id: str, field_name: str, new_value: str):
    """Update metadata field"""
    cli.update_metadata(asset_type, asset_id, field_name, new_value)


@main.command()
@click.argument("asset_type")
@click.argument("asset_id")
@click.option("--unpublish", is_flag=True, help="Unpublish instead of publish")
def publish(asset_type: str, asset_id: str, unpublish: bool):
    """Publish or unpublish an asset"""
    cli.publish_asset(asset_type, asset_id, unpublish)


@main.command()
@click.argument("asset_type")
@click.argument("path_pattern")
@click.argument("field_name")
@click.argument("new_value")
@click.option("--site", help="Site name to limit search")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be updated without making changes"
)
def batch_update(
    asset_type: str,
    path_pattern: str,
    field_name: str,
    new_value: str,
    site: Optional[str],
    dry_run: bool,
):
    """Batch update metadata for assets matching type and path pattern"""
    results = cli.batch_update_metadata(
        asset_type, path_pattern, field_name, new_value, site, dry_run
    )
    click.echo(
        f"\n📊 Batch update results: {results['success']} successful, {results['failed']} failed, {results['skipped']} skipped"
    )


@main.command()
@click.argument("asset_type")
@click.argument("path_pattern")
@click.argument("tag_name")
@click.argument("tag_value")
@click.option("--site", help="Site name to limit search")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be updated without making changes"
)
def batch_tag(
    asset_type: str,
    path_pattern: str,
    tag_name: str,
    tag_value: str,
    site: Optional[str],
    dry_run: bool,
):
    """Batch set tag value for assets matching type and path pattern"""
    results = cli.batch_set_tag(
        asset_type, path_pattern, tag_name, tag_value, site, dry_run
    )
    click.echo(
        f"\n📊 Batch tag results: {results['success']} successful, {results['failed']} failed, {results['skipped']} skipped"
    )


@main.command()
@click.argument("asset_type")
@click.argument("path_pattern")
@click.option("--site", help="Site name to limit search")
@click.option("--unpublish", is_flag=True, help="Unpublish instead of publish")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be published without making changes",
)
def batch_publish(
    asset_type: str,
    path_pattern: str,
    site: Optional[str],
    unpublish: bool,
    dry_run: bool,
):
    """Batch publish/unpublish assets matching type and path pattern"""
    results = cli.batch_publish_assets(
        asset_type, path_pattern, unpublish, site, dry_run
    )
    action = "unpublish" if unpublish else "publish"
    click.echo(
        f"\n📊 Batch {action.capitalize()} results: {results['success']} successful, {results['failed']} failed, {results['skipped']} skipped"
    )


@main.command("batch-tag")
@click.argument("asset_type", type=click.Choice(["page", "file", "folder", "format"]))
@click.argument("path_filter")
@click.argument("tag_name")
@click.option("--site", help="Site name to limit search to")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def batch_tag(asset_type, path_filter, tag_name, site, dry_run):
    """Set a tag on multiple assets matching type and path filter"""
    results = cli.batch_set_tag(asset_type, path_filter, tag_name, site, dry_run)
    click.echo(f"📊 Results: {results['success']} successful, {results['failed']} failed")


@main.command("tag-add")
@click.argument("asset_type", type=click.Choice(["page", "file", "folder", "format"]))
@click.argument("asset_id")
@click.argument("tag_name")
def tag_add(asset_type, asset_id, tag_name):
    """Add a tag to a specific asset"""
    if not cli.connected:
        click.echo("❌ Not connected. Use setup first.")
        return
    
    from cascade_rest.tags import add_asset_tags
    result = add_asset_tags(cli.cms_path, cli.auth, asset_id, asset_type, [tag_name])
    
    if result.get("success"):
        click.echo(f"✅ Added tag '{tag_name}' to {asset_type}/{asset_id}")
    else:
        click.echo(f"❌ Failed to add tag: {result}")


@main.command("tag-remove")
@click.argument("asset_type", type=click.Choice(["page", "file", "folder", "format"]))
@click.argument("asset_id")
@click.argument("tag_name")
def tag_remove(asset_type, asset_id, tag_name):
    """Remove a tag from a specific asset"""
    if not cli.connected:
        click.echo("❌ Not connected. Use setup first.")
        return
    
    from cascade_rest.tags import remove_asset_tags
    result = remove_asset_tags(cli.cms_path, cli.auth, asset_id, asset_type, [tag_name])
    
    if result.get("success"):
        click.echo(f"✅ Removed tag '{tag_name}' from {asset_type}/{asset_id}")
    else:
        click.echo(f"❌ Failed to remove tag: {result}")


@main.command("tag-replace")
@click.argument("asset_type", type=click.Choice(["page", "file", "folder", "format"]))
@click.argument("asset_id")
@click.argument("old_tag_name")
@click.argument("new_tag_name")
def tag_replace(asset_type, asset_id, old_tag_name, new_tag_name):
    """Replace an existing tag with a new tag, or add the new tag if old tag doesn't exist"""
    if not cli.connected:
        click.echo("❌ Not connected. Use setup first.")
        return
    
    from cascade_rest.metadata import set_or_replace_single_asset_tag
    result = set_or_replace_single_asset_tag(cli.cms_path, cli.auth, asset_type, asset_id, old_tag_name, new_tag_name)
    
    if result:
        click.echo(f"✅ Replaced tag '{old_tag_name}' with '{new_tag_name}' on {asset_type}/{asset_id}")
    else:
        click.echo(f"❌ Failed to replace tag: {result}")


@main.command("tag-list")
@click.argument("asset_type", type=click.Choice(["page", "file", "folder", "format"]))
@click.argument("asset_id")
def tag_list(asset_type, asset_id):
    """List tags for a specific asset"""
    if not cli.connected:
        click.echo("❌ Not connected. Use setup first.")
        return
    
    from cascade_rest.tags import get_asset_tags
    result = get_asset_tags(cli.cms_path, cli.auth, asset_id, asset_type)
    
    if result.get("success"):
        tags = result.get("tags", [])
        if tags:
            tag_names = [tag.get("name", "") for tag in tags]
            click.echo(f"🏷️  Tags for {asset_type}/{asset_id}: {', '.join(tag_names)}")
        else:
            click.echo(f"🏷️  No tags found for {asset_type}/{asset_id}")
    else:
        click.echo(f"❌ Failed to get tags: {result}")


@main.command("tag-search")
@click.argument("tag_name")
@click.option("--site", help="Site name to limit search to")
@click.option("--type", "asset_type", type=click.Choice(["page", "file", "folder", "format"]), help="Asset type to search")
def tag_search(tag_name, site, asset_type):
    """Search for assets that have a specific tag"""
    if not cli.connected:
        click.echo("❌ Not connected. Use setup first.")
        return
    
    from cascade_rest.tags import search_assets_by_tag
    
    asset_types = [asset_type] if asset_type else None
    result = search_assets_by_tag(cli.cms_path, cli.auth, tag_name, site, asset_types)
    
    if result.get("success"):
        assets = result.get("assets", [])
        if assets:
            click.echo(f"🔍 Found {len(assets)} assets with tag '{tag_name}':")
            for asset in assets[:10]:  # Show first 10
                click.echo(f"  {asset['type']}/{asset['id']} - {asset['path']['path']}")
            if len(assets) > 10:
                click.echo(f"  ... and {len(assets) - 10} more")
        else:
            click.echo(f"🔍 No assets found with tag '{tag_name}'")
    else:
        click.echo(f"❌ Search failed: {result}")


@main.command()
def reports():
    """Show operation reports"""
    cli.show_reports()


@main.command()
def interactive():
    """Start interactive mode"""
    if not cli.connected:
        click.echo("Setting up connection first...")
        if not cli.setup_connection(cli.cms_path or "https://cms.example.edu:8443"):
            click.echo("❌ Cannot start interactive mode without connection")
            return

    click.echo("\n🎯 Cascade REST Interactive Mode")
    click.echo("Type 'help' for commands, 'quit' to exit")

    while True:
        try:
            command = click.prompt("\ncascade>", type=str)

            if command.lower() in ["quit", "exit", "q"]:
                break
            elif command.lower() == "help":
                show_interactive_help()
            elif command.lower() == "status":
                show_status()
            elif command.lower() == "reports":
                cli.show_reports()
            elif command.startswith("read "):
                handle_read_command(command)
            elif command.startswith("search "):
                handle_search_command(command)
            elif command.startswith("ls "):
                handle_ls_command(command)
            elif command.startswith("update "):
                handle_update_command(command)
            elif command.startswith("publish "):
                handle_publish_command(command)
            elif command.startswith("batch-update "):
                handle_batch_update_command(command)
            elif command.startswith("batch-tag "):
                handle_batch_tag_command(command)
            elif command.startswith("batch-publish "):
                handle_batch_publish_command(command)
            else:
                click.echo("❌ Unknown command. Type 'help' for available commands.")

        except KeyboardInterrupt:
            click.echo("\n👋 Goodbye!")
            break
        except Exception as e:
            click.echo(f"❌ Error: {e}")


def show_interactive_help():
    """Show help for interactive mode"""
    help_text = """
Available commands:
  read <type> <id>           - Read a single asset
  search <terms> [--site s]  - Search for assets
  ls <folder_id>             - List folder children
  update <type> <id> <field> <value> - Update metadata
  publish <type> <id> [--unpublish] - Publish/unpublish asset
  batch-update <type> <path> <field> <value> [--site s] [--dry-run] - Batch update metadata
  batch-tag <type> <path> <tag> <value> [--site s] [--dry-run] - Batch set tag
  batch-publish <type> <path> [--site s] [--unpublish] [--dry-run] - Batch publish/unpublish
  reports                    - Show operation reports
  status                     - Show connection status
  help                       - Show this help
  quit                       - Exit interactive mode
    """
    click.echo(help_text)


def show_status():
    """Show connection status"""
    if cli.connected:
        click.echo(f"✅ Connected to {cli.cms_path}")
    else:
        click.echo("❌ Not connected")


def handle_read_command(command: str):
    """Handle read command in interactive mode"""
    parts = command.split()
    if len(parts) != 3:
        click.echo("❌ Usage: read <type> <id>")
        return

    _, asset_type, asset_id = parts
    result = cli.read_asset(asset_type, asset_id)
    if result:
        click.echo(json.dumps(result, indent=2))


def handle_search_command(command: str):
    """Handle search command in interactive mode"""
    parts = command.split()
    if len(parts) < 2:
        click.echo("❌ Usage: search <terms> [--site site_name]")
        return

    search_terms = parts[1]
    site_name = None

    # Parse --site option
    if "--site" in parts:
        site_index = parts.index("--site")
        if site_index + 1 < len(parts):
            site_name = parts[site_index + 1]

    result = cli.search_assets(search_terms, site_name)
    if result:
        click.echo(json.dumps(result, indent=2))


def handle_ls_command(command: str):
    """Handle ls command in interactive mode"""
    parts = command.split()
    if len(parts) != 2:
        click.echo("❌ Usage: ls <folder_id>")
        return

    _, folder_id = parts
    children = cli.get_folder_children(folder_id)
    if children:
        click.echo(f"Found {len(children)} children:")
        for child in children:
            click.echo(f"  {child['type']}: {child['name']} (ID: {child['id']})")


def handle_update_command(command: str):
    """Handle update command in interactive mode"""
    parts = command.split()
    if len(parts) != 5:
        click.echo("❌ Usage: update <type> <id> <field> <value>")
        return

    _, asset_type, asset_id, field_name, new_value = parts
    cli.update_metadata(asset_type, asset_id, field_name, new_value)


def handle_publish_command(command: str):
    """Handle publish command in interactive mode"""
    parts = command.split()
    if len(parts) < 3:
        click.echo("❌ Usage: publish <type> <id> [--unpublish]")
        return

    _, asset_type, asset_id = parts[:3]
    unpublish = "--unpublish" in parts

    cli.publish_asset(asset_type, asset_id, unpublish)


def handle_batch_update_command(command: str):
    """Handle batch-update command in interactive mode"""
    parts = command.split()
    if len(parts) < 5:
        click.echo(
            "❌ Usage: batch-update <type> <path> <field> <value> [--site site] [--dry-run]"
        )
        return

    _, asset_type, path_pattern, field_name, new_value = parts[:5]
    site_name = None
    dry_run = "--dry-run" in parts

    # Parse --site option
    if "--site" in parts:
        site_index = parts.index("--site")
        if site_index + 1 < len(parts):
            site_name = parts[site_index + 1]

    results = cli.batch_update_metadata(
        asset_type, path_pattern, field_name, new_value, site_name, dry_run
    )
    click.echo(
        f"📊 Results: {results['success']} successful, {results['failed']} failed, {results['skipped']} skipped"
    )


def handle_batch_tag_command(command: str):
    """Handle batch-tag command in interactive mode"""
    parts = command.split()
    if len(parts) < 4:
        click.echo(
            "❌ Usage: batch-tag <type> <path> <tag> [--site site] [--dry-run]"
        )
        return

    _, asset_type, path_pattern, tag_name = parts[:4]
    site_name = None
    dry_run = "--dry-run" in parts

    # Parse --site option
    if "--site" in parts:
        site_index = parts.index("--site")
        if site_index + 1 < len(parts):
            site_name = parts[site_index + 1]

    results = cli.batch_set_tag(
        asset_type, path_pattern, tag_name, site_name, dry_run
    )
    click.echo(
        f"📊 Results: {results['success']} successful, {results['failed']} failed"
    )


def handle_batch_publish_command(command: str):
    """Handle batch-publish command in interactive mode"""
    parts = command.split()
    if len(parts) < 3:
        click.echo(
            "❌ Usage: batch-publish <type> <path> [--site site] [--unpublish] [--dry-run]"
        )
        return

    _, asset_type, path_pattern = parts[:3]
    site_name = None
    unpublish = "--unpublish" in parts
    dry_run = "--dry-run" in parts

    # Parse --site option
    if "--site" in parts:
        site_index = parts.index("--site")
        if site_index + 1 < len(parts):
            site_name = parts[site_index + 1]

    results = cli.batch_publish_assets(
        asset_type, path_pattern, unpublish, site_name, dry_run
    )
    action = "unpublish" if unpublish else "publish"
    click.echo(
        f"📊 {action.capitalize()} results: {results['success']} successful, {results['failed']} failed, {results['skipped']} skipped"
    )


# Enhanced commands with new features


@main.command("csv-import")
@click.argument("filename")
@click.option(
    "--operation",
    type=click.Choice(["metadata", "tags"]),
    default="metadata",
    help="Type of operation to perform",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be updated without making changes"
)
def csv_import(filename: str, operation: str, dry_run: bool):
    """Import and process assets from CSV file"""
    if not cli.connected:
        click.echo("❌ Please run 'setup' command first")
        return

    try:
        results = csv_ops.batch_update_from_csv(filename, operation, cli)
        click.echo(f"\n📊 CSV Import Results:")
        click.echo(f"  Total: {results['total']}")
        click.echo(f"  Successful: {results['successful']}")
        click.echo(f"  Failed: {results['failed']}")
        click.echo(f"  Skipped: {results['skipped']}")

        if results["errors"]:
            click.echo(f"\n❌ Errors:")
            for error in results["errors"][:5]:  # Show first 5 errors
                click.echo(f"  {error['asset_id']}: {error['error']}")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@main.command("export-csv")
@click.argument("asset_type")
@click.argument("path_pattern")
@click.argument("output_file")
@click.option("--site", help="Site name to limit search")
@click.option(
    "--include-metadata", is_flag=True, help="Include metadata fields in export"
)
def export_csv(
    asset_type: str,
    path_pattern: str,
    output_file: str,
    site: Optional[str],
    include_metadata: bool,
):
    """Export assets to CSV file"""
    if not cli.connected:
        click.echo("❌ Please run 'setup' command first")
        return

    try:
        # Search for assets
        search_results = cli.search_assets(asset_type, path_pattern, site)

        if not search_results:
            click.echo("❌ No assets found matching criteria")
            return

        # Export to CSV
        csv_path = csv_ops.export_assets_to_csv(
            search_results, output_file, include_metadata
        )
        click.echo(f"✅ Exported {len(search_results)} assets to {csv_path}")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@main.command("csv-template")
@click.argument("asset_type")
@click.option(
    "--filename", default=None, help="Output filename (defaults to template_<type>.csv)"
)
def csv_template(asset_type: str, filename: Optional[str]):
    """Create CSV template for asset type"""
    if filename is None:
        filename = f"template_{asset_type}.csv"

    try:
        template_path = csv_ops.create_template_csv(asset_type, filename)
        click.echo(f"✅ Created template: {template_path}")
        click.echo(
            f"💡 Edit the template with your data, then use 'csv-import' to process it"
        )
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@main.command("rollback-list")
@click.option("--limit", default=20, help="Number of rollback records to show")
def rollback_list(limit: int):
    """List available rollback operations"""
    try:
        records = rollback_manager.list_rollback_records(limit)

        if not records:
            click.echo("📋 No rollback records found")
            return

        click.echo(f"\n📋 Rollback Records (showing {len(records)} of {limit}):")
        click.echo("-" * 80)

        for record in records:
            status_emoji = "✅" if record["status"] == "completed" else "⏳"
            click.echo(
                f"{status_emoji} {record['operation_id'][:8]}... | {record['operation_type']} | "
                f"{record['asset_count']} assets | {record['timestamp'][:19]}"
            )
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@main.command("rollback-execute")
@click.argument("operation_id")
def rollback_execute(operation_id: str):
    """Execute a rollback operation"""
    if not cli.connected:
        click.echo("❌ Please run 'setup' command first")
        return

    try:
        results = rollback_manager.execute_rollback(operation_id)
        click.echo(f"\n📊 Rollback Results:")
        click.echo(f"  Successful: {results['successful_rollbacks']}")
        click.echo(f"  Failed: {results['failed_rollbacks']}")

        if results["errors"]:
            click.echo(f"\n❌ Errors:")
            for error in results["errors"][:5]:
                click.echo(f"  {error['asset_id']}: {error['error']}")
    except Exception as e:
        click.echo(f"❌ Error: {e}")


@main.command("advanced-search")
@click.argument("asset_type")
@click.argument("path_pattern")
@click.option("--field", help="Field to filter on")
@click.option(
    "--operator", type=click.Choice(advanced_filter.operators), help="Filter operator"
)
@click.option("--value", help="Filter value")
@click.option("--case-sensitive", is_flag=True, help="Case sensitive matching")
@click.option("--site", help="Site name to limit search")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be updated without making changes"
)
def advanced_search(
    asset_type: str,
    path_pattern: str,
    field: Optional[str],
    operator: Optional[str],
    value: Optional[str],
    case_sensitive: bool,
    site: Optional[str],
    dry_run: bool,
):
    """Advanced search with filtering capabilities"""
    if not cli.connected:
        click.echo("❌ Please run 'setup' command first")
        return

    try:
        # Basic search first
        search_results = cli.search_assets(asset_type, path_pattern, site)

        if not search_results:
            click.echo("❌ No assets found matching basic criteria")
            return

        click.echo(f"🔍 Found {len(search_results)} assets with basic criteria")

        # Apply advanced filters if provided
        if field and operator and value:
            filter_expr = advanced_filter.create_filter_expression(
                field, operator, value, case_sensitive
            )
            filtered_results = advanced_filter.apply_filters(
                search_results, [filter_expr]
            )

            click.echo(f"🎯 {len(filtered_results)} assets match advanced filter")

            if dry_run:
                click.echo(f"\n📋 Assets that would be processed:")
                for asset in filtered_results[:10]:  # Show first 10
                    click.echo(
                        f"  {asset.get('id', 'N/A')} - {asset.get('name', 'N/A')}"
                    )
                if len(filtered_results) > 10:
                    click.echo(f"  ... and {len(filtered_results) - 10} more")
            else:
                # Display results
                click.echo(f"\n📋 Matching Assets:")
                for asset in filtered_results[:20]:  # Show first 20
                    click.echo(
                        f"  {asset.get('id', 'N/A')} - {asset.get('name', 'N/A')}"
                    )
                if len(filtered_results) > 20:
                    click.echo(f"  ... and {len(filtered_results) - 20} more")
        else:
            # Display basic results
            click.echo(f"\n📋 Assets:")
            for asset in search_results[:20]:
                click.echo(f"  {asset.get('id', 'N/A')} - {asset.get('name', 'N/A')}")
            if len(search_results) > 20:
                click.echo(f"  ... and {len(search_results) - 20} more")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


@main.command("performance-stats")
def performance_stats():
    """Show performance statistics"""
    try:
        metrics = performance_monitor.get_metrics()

        click.echo(f"\n📊 Performance Statistics:")
        click.echo(f"  Total Operations: {metrics['total_operations']}")
        click.echo(f"  Successful: {metrics['successful_operations']}")
        click.echo(f"  Failed: {metrics['failed_operations']}")
        click.echo(f"  Average Time: {metrics['average_time']:.2f}s")
        click.echo(f"  Operations/sec: {metrics['operations_per_second']:.2f}")

        cache_stats = {
            "cached_items": len(cache_manager.cache),
            "cache_hits": "N/A",  # Would need to implement hit tracking
            "cache_misses": "N/A",
        }
        click.echo(f"\n💾 Cache Statistics:")
        click.echo(f"  Cached Items: {cache_stats['cached_items']}")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


@main.command()
def cleanup():
    """Clean up old rollback records and cache"""
    try:
        # Cleanup rollback records
        removed_rollbacks = rollback_manager.cleanup_old_rollbacks()

        # Cleanup cache
        removed_cache = cache_manager.cleanup_expired()

        click.echo(f"🧹 Cleanup Results:")
        click.echo(f"  Removed {removed_rollbacks} old rollback records")
        click.echo(f"  Removed {removed_cache} expired cache entries")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


@main.command()
@click.argument("connection_name")
def connect(connection_name: str):
    """Connect using a stored connection"""
    connection_data = secrets_manager.get_connection(connection_name)

    if not connection_data:
        click.echo(f"❌ Connection '{connection_name}' not found")
        click.echo("💡 Use 'python cli.py setup' to create a connection first")
        return

    # Set up the connection
    cli.setup_connection(
        connection_data["cms_path"],
        connection_data.get("api_key"),
        connection_data.get("username"),
        connection_data.get("password"),
    )

    click.echo(f"✅ Connected using '{connection_name}'")


@main.command("connections")
def list_connections():
    """List all stored connections"""
    connections = secrets_manager.list_connections()

    if not connections:
        click.echo("📋 No stored connections found")
        click.echo("💡 Use 'python cli.py setup' to create a connection")
        return

    click.echo(f"\n📋 Stored Connections ({len(connections)}):")
    click.echo("-" * 80)

    for name, data in connections.items():
        auth_type_display = {
            "api_key_encrypted": "API Key (Encrypted)",
            "api_key_keyring": "API Key (Keyring)",
            "username_password_encrypted": "Username/Password (Encrypted)",
            "username_password_keyring": "Username/Password (Keyring)",
        }.get(data["auth_type"], data["auth_type"])

        click.echo(f"🔗 {name}")
        click.echo(f"   URL: {data['cms_path']}")
        click.echo(f"   Auth: {auth_type_display}")
        click.echo(f"   Created: {data['created'][:19]}")
        click.echo()


@main.command("delete-connection")
@click.argument("connection_name")
def delete_connection(connection_name: str):
    """Delete a stored connection"""
    if secrets_manager.delete_connection(connection_name):
        click.echo(f"✅ Connection '{connection_name}' deleted")
    else:
        click.echo(f"❌ Connection '{connection_name}' not found")


@main.command("interactive-setup")
@click.option("--connection-name", default="default", help="Name for this connection")
def interactive_setup(connection_name: str):
    """Interactive setup for storing connection details"""
    success = secrets_manager.interactive_setup(connection_name)

    if success:
        click.echo(f"\n✅ Interactive setup complete!")
        click.echo(
            f"💡 Use 'python cli.py connect {connection_name}' to use this connection"
        )
    else:
        click.echo("\n❌ Interactive setup failed")


@main.command("test-environments")
def list_test_environments():
    """List all test environments"""
    test_envs = test_manager.list_test_environments()

    if not test_envs:
        click.echo("🧪 No test environments found")
        click.echo("💡 Create test environments with:")
        click.echo(
            "   python cli.py setup --cms-path 'https://test-cms.example.com' --connection-name 'test'"
        )
        return

    click.echo(f"\n🧪 Test Environments ({len(test_envs)}):")
    click.echo("-" * 80)

    for env in test_envs:
        click.echo(f"🔬 {env['name']}")
        click.echo(f"   URL: {env['url']}")
        click.echo(f"   Auth: {env['auth_type']}")
        if env["description"]:
            click.echo(f"   Description: {env['description']}")
        click.echo(f"   Created: {env['created'][:19]}")
        click.echo()


@main.command("validate-test")
@click.argument("env_name")
def validate_test_environment(env_name: str):
    """Validate a test environment"""
    results = test_manager.validate_test_environment(env_name)

    click.echo(f"\n🔍 Validating test environment: {env_name}")
    click.echo("-" * 50)

    if results["errors"]:
        click.echo("❌ Validation failed:")
        for error in results["errors"]:
            click.echo(f"   • {error}")
    else:
        click.echo("✅ Environment validation successful")
        click.echo(f"   Accessible: {'✅' if results['accessible'] else '❌'}")
        click.echo(f"   API Responsive: {'✅' if results['api_responsive'] else '❌'}")
        click.echo(f"   Auth Valid: {'✅' if results['auth_valid'] else '❌'}")


@main.command("compare-environments")
@click.argument("env1")
@click.argument("env2")
def compare_environments(env1: str, env2: str):
    """Compare two environments"""
    comparison = test_manager.compare_environments(env1, env2)

    if "error" in comparison:
        click.echo(f"❌ {comparison['error']}")
        return

    click.echo(f"\n🔍 Comparing environments:")
    click.echo(f"   {env1} vs {env2}")
    click.echo("-" * 50)
    click.echo(f"URL Match: {'✅' if comparison['url_match'] else '❌'}")
    click.echo(f"Auth Type Match: {'✅' if comparison['auth_type_match'] else '❌'}")


@main.command("test-workflow")
@click.argument("workflow_name")
@click.argument("test_env")
@click.option("--dry-run", is_flag=True, default=True, help="Run in dry-run mode")
def run_test_workflow(workflow_name: str, test_env: str, dry_run: bool):
    """Run a test workflow against a test environment"""

    # First, connect to the test environment
    click.echo(f"🔗 Connecting to test environment: {test_env}")
    connection_data = secrets_manager.get_connection(test_env)

    if not connection_data:
        click.echo(f"❌ Test environment '{test_env}' not found")
        return

    # Set up the connection
    cli.setup_connection(
        connection_data["cms_path"],
        connection_data.get("api_key"),
        connection_data.get("username"),
        connection_data.get("password"),
    )

    click.echo(f"✅ Connected to {test_env}")

    # Run the test workflow
    click.echo(f"🧪 Running test workflow: {workflow_name}")
    results = test_manager.run_test_workflow(workflow_name, test_env, dry_run)

    if "error" in results:
        click.echo(f"❌ {results['error']}")
        return

    click.echo(f"\n📊 Test Workflow Results:")
    click.echo(f"   Operations Run: {results['operations_run']}")
    click.echo(f"   Successful: {results['operations_successful']}")
    click.echo(f"   Failed: {results['operations_failed']}")

    if results["errors"]:
        click.echo(f"\n❌ Errors:")
        for error in results["errors"]:
            click.echo(f"   • {error}")


@main.command("test-setup-helper")
def test_setup_helper():
    """Show test environment setup examples"""
    click.echo("🧪 Test Environment Setup Helper")
    click.echo("=" * 50)

    click.echo("\n📋 Common Test Environment Configurations:")
    click.echo()

    configs = [
        {
            "name": "local_test",
            "url": "http://localhost:8080",
            "description": "Local development instance",
        },
        {
            "name": "staging",
            "url": "https://staging-cms.your-domain.com:8443",
            "description": "Staging environment for pre-production testing",
        },
        {
            "name": "integration_test",
            "url": "https://test-cms.your-domain.com:8443",
            "description": "Integration testing environment",
        },
    ]

    for config in configs:
        click.echo(f"🔬 {config['name']}")
        click.echo(f"   URL: {config['url']}")
        click.echo(f"   Description: {config['description']}")
        click.echo(
            f"   Setup: python cli.py setup --cms-path \"{config['url']}\" --connection-name \"{config['name']}\""
        )
        click.echo()

    click.echo("💡 Best Practices:")
    click.echo("   • Always use --dry-run first when testing operations")
    click.echo("   • Validate test environments before running workflows")
    click.echo("   • Use different connection names for different environments")
    click.echo("   • Store test credentials securely with --use-keyring")


@main.command("connect-1password")
@click.argument("vault")
@click.argument("item")
@click.option(
    "--connection-name", default="1password", help="Name for this connection session"
)
def connect_from_1password(vault: str, item: str, connection_name: str):
    """Connect using credentials from 1Password"""

    click.echo(f"🔑 Fetching credentials from 1Password...")
    click.echo(f"   Vault: {vault}")
    click.echo(f"   Item: {item}")

    connection_data = secrets_manager.get_from_1password(vault, item)

    if not connection_data:
        click.echo("❌ Failed to fetch credentials from 1Password")
        click.echo("💡 Make sure:")
        click.echo("   • 1Password CLI is installed and authenticated")
        click.echo("   • The vault and item exist")
        click.echo("   • The item contains valid Cascade credentials")
        return

    # Set up the connection
    cli.setup_connection(
        connection_data["cms_path"],
        connection_data.get("api_key"),
        connection_data.get("username"),
        connection_data.get("password"),
    )

    # Create persistent session
    session_manager.create_session(
        connection_data["cms_path"],
        connection_data.get("api_key"),
        connection_data.get("username"),
        connection_data.get("password"),
        source=f"1password:{vault}:{item}",
    )

    click.echo(f"✅ Connected using 1Password credentials")
    click.echo(f"   URL: {connection_data['cms_path']}")
    click.echo(
        f"   Auth: {'API Key' if connection_data.get('api_key') else 'Username/Password'}"
    )
    click.echo(f"   Session: Persistent (24 hours)")


@main.command("list-1password")
@click.argument("vault")
def list_1password_items(vault: str):
    """List Cascade-related items in a 1Password vault"""

    click.echo(f"🔍 Searching for Cascade items in vault: {vault}")

    items = secrets_manager.list_1password_items(vault)

    if not items:
        click.echo("📋 No Cascade-related items found")
        click.echo("💡 Make sure:")
        click.echo("   • The vault exists and is accessible")
        click.echo("   • Items contain 'cascade', 'cms', or 'api' in their title")
        return

    click.echo(f"\n📋 Cascade Items in '{vault}' ({len(items)}):")
    click.echo("-" * 80)

    for item in items:
        click.echo(f"🔑 {item['title']}")
        click.echo(f"   ID: {item['id']}")
        click.echo(
            f"   Updated: {item['updated'][:19] if item['updated'] else 'Unknown'}"
        )
        click.echo(
            f"   Connect: python cli.py connect-1password {vault} \"{item['title']}\""
        )
        click.echo()


@main.command("setup-1password")
@click.option("--vault", required=True, help="1Password vault name")
@click.option("--item-name", required=True, help="Name for the 1Password item")
@click.option("--cms-path", help="Cascade Server URL")
@click.option("--api-key", help="API key for authentication")
@click.option("--username", help="Username for authentication")
@click.option("--password", help="Password for authentication")
def setup_with_1password(
    vault: str,
    item_name: str,
    cms_path: str,
    api_key: str,
    username: str,
    password: str,
):
    """Set up connection and store credentials in 1Password"""

    # Get missing information interactively

    if not cms_path:
        cms_path = click.prompt(
            "Cascade Server URL", default="https://cms.example.com:8443"
        )

    if not api_key and not username:
        auth_type = click.prompt(
            "Authentication type",
            type=click.Choice(["api_key", "username_password"]),
            default="api_key",
        )

        if auth_type == "api_key":
            api_key = getpass.getpass("Enter API key: ")
        else:
            username = click.prompt("Username")
            password = getpass.getpass("Password: ")

    # Prepare connection data
    connection_data = {
        "cms_path": cms_path,
        "api_key": api_key,
        "username": username,
        "password": password,
        "created": secrets_manager._get_timestamp(),
    }

    # Store in 1Password
    success = secrets_manager.store_in_1password(vault, item_name, connection_data)

    if success:
        click.echo(f"✅ Credentials stored in 1Password")
        click.echo(f"   Vault: {vault}")
        click.echo(f"   Item: {item_name}")
        click.echo(f'   Connect: python cli.py connect-1password {vault} "{item_name}"')
    else:
        click.echo("❌ Failed to store credentials in 1Password")
        click.echo("💡 Make sure:")
        click.echo("   • 1Password CLI is installed and authenticated")
        click.echo("   • You have access to the specified vault")
        click.echo("   • The vault exists")


@main.command("quick-connect")
@click.option(
    "--env",
    type=click.Choice(["test", "production"]),
    required=True,
    help="Environment to connect to",
)
@click.option(
    "--vault-prefix", default="Cascade", help="Prefix for 1Password vault names"
)
def quick_connect(env: str, vault_prefix: str):
    """Quickly connect to test or production environment using 1Password"""

    vault_name = f"{vault_prefix} {env.title()}"
    item_name = f"{env.title()} Service Account"

    click.echo(f"🚀 Quick connecting to {env} environment...")
    click.echo(f"   Vault: {vault_name}")
    click.echo(f"   Item: {item_name}")

    connection_data = secrets_manager.get_from_1password(vault_name, item_name)

    if not connection_data:
        click.echo(f"❌ Could not find credentials for {env} environment")
        click.echo(f"💡 Expected:")
        click.echo(f"   • Vault: {vault_name}")
        click.echo(f"   • Item: {item_name}")
        click.echo(
            f'💡 Or use: python cli.py connect-1password "{vault_name}" "{item_name}"'
        )
        return

    # Set up the connection
    cli.setup_connection(
        connection_data["cms_path"],
        connection_data.get("api_key"),
        connection_data.get("username"),
        connection_data.get("password"),
    )

    click.echo(f"✅ Connected to {env} environment")
    click.echo(f"   URL: {connection_data['cms_path']}")
    click.echo(
        f"   Auth: {'API Key' if connection_data.get('api_key') else 'Username/Password'}"
    )
    click.echo(
        f"💡 Ready for operations - try: python cli.py search --type page --path-filter '2024-2025' --dry-run"
    )


@main.command("session-info")
def show_session_info():
    """Show current session information"""

    session_info = session_manager.get_session_info()

    if not session_info:
        click.echo("📋 No active session")
        click.echo("💡 Connect with: python cli.py connect-1password 'vault' 'item'")
        return

    click.echo("📋 Active Session:")
    click.echo(f"   URL: {session_info['cms_path']}")
    click.echo(f"   Source: {session_info['source']}")
    click.echo(f"   Created: {session_info['created'][:19]}")
    click.echo(f"   Expires: {session_info['expires'][:19]}")


@main.command("session-clear")
def clear_session():
    """Clear current session"""

    success = session_manager.clear_session()

    if success:
        click.echo("🗑️ Session cleared")
    else:
        click.echo("❌ Failed to clear session")


@main.command("session-extend")
@click.option("--hours", default=24, help="Hours to extend session")
def extend_session(hours: int):
    """Extend current session"""

    success = session_manager.extend_session(hours)

    if success:
        click.echo(f"⏰ Session extended by {hours} hours")
    else:
        click.echo("❌ No active session to extend")


@main.command("job-create")
@click.argument("name")
@click.argument("schedule")
@click.argument("command", nargs=-1)
@click.option(
    "--job-type",
    type=click.Choice([jt.value for jt in JobType]),
    default="custom_command",
    help="Type of job",
)
@click.option(
    "--environment",
    default="production",
    help="Environment to run job in (test, production, or connection name)",
)
@click.option("--enabled/--disabled", default=True, help="Whether job is enabled")
def create_scheduled_job(
    name: str,
    schedule: str,
    command: tuple,
    job_type: str,
    environment: str,
    enabled: bool,
):
    """Create a new scheduled job"""

    if not command:
        click.echo("❌ Command arguments are required")
        click.echo(
            "💡 Example: python cli.py job-create 'Update Faculty' 'daily at 09:00' search --type page --path-filter 'faculty'"
        )
        return

    job_type_enum = JobType(job_type)

    job_id = job_scheduler.create_job(
        name=name,
        job_type=job_type_enum,
        schedule_expr=schedule,
        command_args=list(command),
        environment=environment,
        enabled=enabled,
    )

    click.echo(f"✅ Created scheduled job: {name}")
    click.echo(f"   ID: {job_id}")
    click.echo(f"   Schedule: {schedule}")
    click.echo(f"   Command: {' '.join(command)}")
    click.echo(f"   Environment: {environment}")
    click.echo(f"   Status: {'Enabled' if enabled else 'Disabled'}")


@main.command("job-list")
@click.option("--environment", help="Filter by environment")
@click.option(
    "--status",
    type=click.Choice([js.value for js in JobStatus]),
    help="Filter by status",
)
def list_scheduled_jobs(environment: str, status: str):
    """List all scheduled jobs"""

    jobs = job_scheduler.list_jobs(environment=environment)

    if status:
        status_enum = JobStatus(status)
        jobs = [job for job in jobs if job.status == status_enum]

    if not jobs:
        click.echo("📋 No scheduled jobs found")
        click.echo(
            "💡 Create a job with: python cli.py job-create 'My Job' 'daily at 09:00' search --type page"
        )
        return

    click.echo(f"\n📋 Scheduled Jobs ({len(jobs)}):")
    click.echo("-" * 100)

    for job in jobs:
        status_icon = {
            JobStatus.PENDING: "⏳",
            JobStatus.RUNNING: "🔄",
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌",
            JobStatus.CANCELLED: "⏹️",
        }.get(job.status, "❓")

        click.echo(f"{status_icon} {job.name}")
        click.echo(f"   ID: {job.id}")
        click.echo(f"   Type: {job.job_type.value}")
        click.echo(f"   Schedule: {job.schedule_expr}")
        click.echo(f"   Environment: {job.environment}")
        click.echo(f"   Status: {job.status.value}")
        click.echo(f"   Enabled: {'Yes' if job.enabled else 'No'}")

        if job.next_run:
            click.echo(f"   Next Run: {job.next_run.strftime('%Y-%m-%d %H:%M:%S')}")

        if job.last_run:
            click.echo(f"   Last Run: {job.last_run.strftime('%Y-%m-%d %H:%M:%S')}")

        click.echo(f"   Command: {' '.join(job.command_args)}")
        click.echo()


@main.command("job-run")
@click.argument("job_id")
@click.option("--dry-run", is_flag=True, help="Run in dry-run mode")
def run_scheduled_job(job_id: str, dry_run: bool):
    """Run a scheduled job immediately"""

    job = job_scheduler.get_job(job_id)
    if not job:
        click.echo(f"❌ Job '{job_id}' not found")
        return

    click.echo(f"🚀 Running job: {job.name}")
    click.echo(f"   Command: {' '.join(job.command_args)}")
    if dry_run:
        click.echo("   Mode: Dry run")

    execution = job_scheduler.run_job(job_id, dry_run=dry_run)

    if execution:
        click.echo(f"\n📊 Execution Results:")
        click.echo(f"   Execution ID: {execution.execution_id}")
        click.echo(f"   Status: {execution.status.value}")
        click.echo(
            f"   Duration: {execution.ended - execution.started if execution.ended else 'N/A'}"
        )

        if execution.output:
            click.echo(f"\n📤 Output:")
            click.echo(execution.output)

        if execution.error:
            click.echo(f"\n❌ Error:")
            click.echo(execution.error)


@main.command("job-enable")
@click.argument("job_id")
def enable_scheduled_job(job_id: str):
    """Enable a scheduled job"""

    success = job_scheduler.enable_job(job_id)

    if success:
        job = job_scheduler.get_job(job_id)
        click.echo(f"✅ Enabled job: {job.name}")
    else:
        click.echo(f"❌ Job '{job_id}' not found")


@main.command("job-disable")
@click.argument("job_id")
def disable_scheduled_job(job_id: str):
    """Disable a scheduled job"""

    success = job_scheduler.disable_job(job_id)

    if success:
        job = job_scheduler.get_job(job_id)
        click.echo(f"⏸️ Disabled job: {job.name}")
    else:
        click.echo(f"❌ Job '{job_id}' not found")


@main.command("job-delete")
@click.argument("job_id")
def delete_scheduled_job(job_id: str):
    """Delete a scheduled job"""

    job = job_scheduler.get_job(job_id)
    if not job:
        click.echo(f"❌ Job '{job_id}' not found")
        return

    success = job_scheduler.delete_job(job_id)

    if success:
        click.echo(f"🗑️ Deleted job: {job.name}")
    else:
        click.echo(f"❌ Failed to delete job '{job_id}'")


@main.command("job-history")
@click.argument("job_id")
@click.option("--limit", default=10, help="Number of executions to show")
def show_job_history(job_id: str, limit: int):
    """Show execution history for a job"""

    job = job_scheduler.get_job(job_id)
    if not job:
        click.echo(f"❌ Job '{job_id}' not found")
        return

    executions = job_scheduler.get_job_history(job_id=job_id, limit=limit)

    if not executions:
        click.echo(f"📋 No execution history for job: {job.name}")
        return

    click.echo(f"\n📊 Execution History for: {job.name}")
    click.echo(f"   Job ID: {job_id}")
    click.echo("-" * 80)

    for execution in executions:
        status_icon = {
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌",
            JobStatus.RUNNING: "🔄",
            JobStatus.PENDING: "⏳",
        }.get(execution.status, "❓")

        click.echo(f"{status_icon} {execution.execution_id}")
        click.echo(f"   Started: {execution.started.strftime('%Y-%m-%d %H:%M:%S')}")

        if execution.ended:
            duration = execution.ended - execution.started
            click.echo(f"   Duration: {duration}")
            click.echo(f"   Status: {execution.status.value}")

        if execution.exit_code is not None:
            click.echo(f"   Exit Code: {execution.exit_code}")

        if execution.error:
            click.echo(f"   Error: {execution.error[:100]}...")

        click.echo()


@main.command("scheduler-start")
def start_scheduler():
    """Start the background job scheduler"""

    job_scheduler.start_scheduler()
    click.echo("🚀 Background scheduler started")
    click.echo("💡 Jobs will run automatically according to their schedules")


@main.command("scheduler-stop")
def stop_scheduler():
    """Stop the background job scheduler"""

    job_scheduler.stop_scheduler()
    click.echo("⏹️ Background scheduler stopped")


@main.command("job-cleanup")
@click.option("--days", default=30, help="Number of days of history to keep")
def cleanup_job_history(days: int):
    """Clean up old job execution history"""

    deleted_count = job_scheduler.cleanup_old_executions(days)
    click.echo(f"🧹 Cleaned up {deleted_count} old execution records")
    click.echo(f"💡 Kept execution history for the last {days} days")


@main.command("job-templates")
def show_job_templates():
    """Show example job templates"""

    click.echo("📋 Scheduled Job Templates")
    click.echo("=" * 50)

    templates = [
        {
            "name": "Daily Faculty Update",
            "schedule": "daily at 09:00",
            "command": "batch-update --type page --path-filter 'faculty' --field 'last_updated' --value '$(date)'",
            "description": "Update faculty pages daily",
        },
        {
            "name": "Weekly Course Catalog Sync",
            "schedule": "weekly on Monday at 06:00",
            "command": "csv-import courses.csv --operation metadata --dry-run",
            "description": "Sync course catalog from CSV weekly",
        },
        {
            "name": "Academic Year Tag Update",
            "schedule": "every 1 day",
            "command": "batch-tag --type page --path-filter '2024-2025' --tag 'academic_year' --value '2024-2025'",
            "description": "Update academic year tags daily",
        },
        {
            "name": "Monthly Cleanup",
            "schedule": "every 30 days",
            "command": "cleanup --days 30",
            "description": "Clean up old rollback records and cache monthly",
        },
    ]

    for template in templates:
        click.echo(f"\n🔧 {template['name']}")
        click.echo(f"   Schedule: {template['schedule']}")
        click.echo(f"   Command: {template['command']}")
        click.echo(f"   Description: {template['description']}")
        click.echo(
            f"   Create: python cli.py job-create '{template['name']}' '{template['schedule']}' {template['command']}"
        )

    click.echo(f"\n💡 Schedule Format Examples:")
    click.echo(f"   • 'daily at 09:00' - Run daily at 9 AM")
    click.echo(f"   • 'every 30 minutes' - Run every 30 minutes")
    click.echo(f"   • 'every 2 hours' - Run every 2 hours")
    click.echo(f"   • 'weekly on Monday at 06:00' - Run weekly on Monday at 6 AM")


if __name__ == "__main__":
    main()
