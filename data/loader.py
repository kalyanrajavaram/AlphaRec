"""
Data Loader Module - Load user data and tool database.

Provides a clean interface for loading data from various sources.
Currently supports CSV exports; designed to be extensible.
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads user behavior data and tool database.

    Usage:
        loader = DataLoader(config)
        user_data = loader.load_user_data()
        tools = loader.load_tools()
    """

    def __init__(self, config: Dict[str, Any]):
        data_config = config.get("data", {})
        self.exports_dir = Path(data_config.get("exports_dir", "exports"))
        self.tools_file = Path(data_config.get("tools_file", "ai_tools_cleaned.json"))

    def load_user_data(self) -> Dict[str, Any]:
        """
        Load all user behavior data from CSV exports.

        Returns:
            Dictionary with browsing_history, search_queries,
            application_usage, and user_interactions
        """
        user_data = {
            "browsing_history": [],
            "search_queries": [],
            "application_usage": [],
            "user_interactions": []
        }

        # Load browsing history
        browsing_path = self.exports_dir / "browsing_history.csv"
        user_data["browsing_history"] = self._load_csv(
            browsing_path,
            field_types={
                "duration_seconds": int,
                "active_duration_seconds": int
            }
        )
        logger.info(f"Loaded {len(user_data['browsing_history'])} browsing entries")

        # Load search queries
        search_path = self.exports_dir / "search_queries.csv"
        user_data["search_queries"] = self._load_csv(search_path)
        logger.info(f"Loaded {len(user_data['search_queries'])} search queries")

        # Load application usage
        app_path = self.exports_dir / "application_usage.csv"
        user_data["application_usage"] = self._load_csv(
            app_path,
            field_types={"duration_seconds": int}
        )
        logger.info(f"Loaded {len(user_data['application_usage'])} app usage entries")

        # Load user interactions
        interactions_path = self.exports_dir / "user_interactions.csv"
        user_data["user_interactions"] = self._load_csv(interactions_path)
        logger.info(f"Loaded {len(user_data['user_interactions'])} interactions")

        return user_data

    def _load_csv(
        self,
        path: Path,
        field_types: Optional[Dict[str, type]] = None
    ) -> List[Dict[str, Any]]:
        """
        Load a CSV file into a list of dictionaries.

        Args:
            path: Path to CSV file
            field_types: Optional dict mapping field names to types for conversion

        Returns:
            List of dictionaries (one per row)
        """
        field_types = field_types or {}
        rows = []

        if not path.exists():
            logger.warning(f"CSV file not found: {path}")
            return rows

        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Convert types where specified
                    for field, target_type in field_types.items():
                        if field in row:
                            try:
                                value = row[field]
                                if value == '' or value is None:
                                    row[field] = 0 if target_type in (int, float) else None
                                else:
                                    row[field] = target_type(value)
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Type conversion failed for {field}: {e}")
                                row[field] = 0 if target_type in (int, float) else None

                    rows.append(row)

        except Exception as e:
            logger.error(f"Failed to load CSV {path}: {e}")

        return rows

    def load_tools(self) -> List[Dict[str, Any]]:
        """
        Load the AI tools database.

        Returns:
            List of tool dictionaries
        """
        if not self.tools_file.exists():
            logger.error(f"Tools file not found: {self.tools_file}")
            return []

        try:
            with open(self.tools_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            tools = data.get("tools", [])
            logger.info(f"Loaded {len(tools)} AI tools")

            # Filter out tools with missing essential data
            valid_tools = []
            for tool in tools:
                tool_data = tool.get("data", {})
                if tool_data.get("name") and tool_data.get("description"):
                    valid_tools.append(tool)

            if len(valid_tools) < len(tools):
                logger.info(f"Filtered to {len(valid_tools)} valid tools")

            return valid_tools

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in tools file: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load tools: {e}")
            return []

    def get_data_stats(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about loaded user data.

        Returns:
            Dictionary with counts and summaries
        """
        stats = {
            "browsing_entries": len(user_data.get("browsing_history", [])),
            "search_queries": len(user_data.get("search_queries", [])),
            "app_usage_entries": len(user_data.get("application_usage", [])),
            "interactions": len(user_data.get("user_interactions", []))
        }

        # Calculate total browsing time
        total_seconds = sum(
            entry.get("active_duration_seconds") or entry.get("duration_seconds") or 0
            for entry in user_data.get("browsing_history", [])
        )
        stats["total_browsing_minutes"] = round(total_seconds / 60, 1)

        # Calculate total app time
        total_app_seconds = sum(
            entry.get("duration_seconds", 0) or 0
            for entry in user_data.get("application_usage", [])
        )
        stats["total_app_minutes"] = round(total_app_seconds / 60, 1)

        # Count unique domains
        domains = set()
        for entry in user_data.get("browsing_history", []):
            url = entry.get("url", "")
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                domains.add(domain)
        stats["unique_domains"] = len(domains)

        # Count unique apps
        apps = set(
            entry.get("app_name", "")
            for entry in user_data.get("application_usage", [])
        )
        stats["unique_apps"] = len(apps - {""})

        return stats


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return {}

    with open(path, 'r') as f:
        return yaml.safe_load(f)
