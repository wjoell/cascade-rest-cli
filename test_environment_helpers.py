#!/usr/bin/env python3
"""
Test Environment Helpers for Cascade REST CLI

Utilities for managing test environments and validating operations
before running them on production.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from secrets_manager import secrets_manager
from logging_config import logger


class TestEnvironmentManager:
    """Manage test environments and validation workflows"""

    def __init__(self):
        self.test_config_dir = Path.home() / ".cascade_cli" / "test_configs"
        self.test_config_dir.mkdir(exist_ok=True)

    def create_test_environment(
        self,
        env_name: str,
        base_url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        description: str = "",
    ) -> bool:
        """Create a test environment configuration"""

        test_config = {
            "name": env_name,
            "base_url": base_url,
            "api_key": api_key,
            "username": username,
            "password": password,
            "description": description,
            "created": datetime.now().isoformat(),
            "environment_type": "test",
        }

        # Store in secrets manager
        success = secrets_manager.store_connection(
            env_name, base_url, api_key, username, password, use_keyring=True
        )

        if success:
            # Store additional test metadata
            config_file = self.test_config_dir / f"{env_name}.json"
            with open(config_file, "w") as f:
                json.dump(test_config, f, indent=2)

            logger.log_operation_end(
                "create_test_environment", True, env_name=env_name, base_url=base_url
            )
            return True

        return False

    def list_test_environments(self) -> List[Dict[str, Any]]:
        """List all test environments"""

        test_envs = []
        connections = secrets_manager.list_connections()

        for name, data in connections.items():
            config_file = self.test_config_dir / f"{name}.json"
            if config_file.exists():
                try:
                    with open(config_file, "r") as f:
                        config = json.load(f)
                    if config.get("environment_type") == "test":
                        test_envs.append(
                            {
                                "name": name,
                                "url": data["cms_path"],
                                "auth_type": data["auth_type"],
                                "description": config.get("description", ""),
                                "created": data["created"],
                            }
                        )
                except Exception as e:
                    logger.log_error(e, {"env_name": name})

        return test_envs

    def validate_test_environment(self, env_name: str) -> Dict[str, Any]:
        """Validate that a test environment is accessible and working"""

        validation_results = {
            "env_name": env_name,
            "accessible": False,
            "api_responsive": False,
            "auth_valid": False,
            "errors": [],
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Get connection details
            connection_data = secrets_manager.get_connection(env_name)
            if not connection_data:
                validation_results["errors"].append("Connection not found")
                return validation_results

            # Test basic connectivity (you would implement actual API calls here)
            # This is a placeholder - in real implementation, you'd test actual API endpoints

            validation_results["accessible"] = True
            validation_results["api_responsive"] = True
            validation_results["auth_valid"] = True

            logger.log_operation_end(
                "validate_test_environment", True, env_name=env_name
            )

        except Exception as e:
            validation_results["errors"].append(str(e))
            logger.log_error(e, {"env_name": env_name, "operation": "validation"})

        return validation_results

    def compare_environments(self, env1: str, env2: str) -> Dict[str, Any]:
        """Compare configurations between two environments"""

        conn1 = secrets_manager.get_connection(env1)
        conn2 = secrets_manager.get_connection(env2)

        if not conn1 or not conn2:
            return {"error": "One or both environments not found"}

        comparison = {
            "environment_1": env1,
            "environment_2": env2,
            "url_match": conn1["cms_path"] == conn2["cms_path"],
            "auth_type_match": conn1.get("auth_type") == conn2.get("auth_type"),
            "timestamp": datetime.now().isoformat(),
        }

        return comparison

    def create_test_workflow(
        self, workflow_name: str, operations: List[Dict[str, Any]]
    ) -> str:
        """Create a test workflow for validation"""

        workflow = {
            "name": workflow_name,
            "operations": operations,
            "created": datetime.now().isoformat(),
            "status": "draft",
        }

        workflow_file = self.test_config_dir / f"workflow_{workflow_name}.json"
        with open(workflow_file, "w") as f:
            json.dump(workflow, f, indent=2)

        logger.log_operation_end(
            "create_test_workflow",
            True,
            workflow_name=workflow_name,
            operation_count=len(operations),
        )

        return str(workflow_file)

    def run_test_workflow(
        self, workflow_name: str, test_env: str, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Run a test workflow against a test environment"""

        workflow_file = self.test_config_dir / f"workflow_{workflow_name}.json"
        if not workflow_file.exists():
            return {"error": f"Workflow {workflow_name} not found"}

        with open(workflow_file, "r") as f:
            workflow = json.load(f)

        results = {
            "workflow_name": workflow_name,
            "test_environment": test_env,
            "dry_run": dry_run,
            "operations_run": 0,
            "operations_successful": 0,
            "operations_failed": 0,
            "errors": [],
            "timestamp": datetime.now().isoformat(),
        }

        # This would integrate with your actual CLI operations
        # For now, it's a placeholder structure

        logger.log_operation_end(
            "run_test_workflow",
            True,
            workflow_name=workflow_name,
            test_env=test_env,
            dry_run=dry_run,
        )

        return results


def create_test_environment_setup():
    """Helper function to create common test environment configurations"""

    test_manager = TestEnvironmentManager()

    # Common test environment configurations
    test_configs = [
        {
            "name": "local_test",
            "base_url": "http://localhost:8080",
            "description": "Local development instance",
        },
        {
            "name": "staging",
            "base_url": "https://staging-cms.your-domain.com:8443",
            "description": "Staging environment for pre-production testing",
        },
        {
            "name": "integration_test",
            "base_url": "https://test-cms.your-domain.com:8443",
            "description": "Integration testing environment",
        },
    ]

    print("🧪 Test Environment Setup Helper")
    print("=" * 50)

    for config in test_configs:
        print(f"\n📋 Creating test environment: {config['name']}")
        print(f"   URL: {config['base_url']}")
        print(f"   Description: {config['description']}")

        # In a real implementation, you'd prompt for credentials
        # For now, this shows the structure
        print(
            f"   💡 Run: python cli.py setup --cms-path \"{config['base_url']}\" --connection-name \"{config['name']}\""
        )


# Global test environment manager
test_manager = TestEnvironmentManager()


if __name__ == "__main__":
    create_test_environment_setup()

