"""
Utility functions for Cascade Server REST API

Handles reporting, logging, and common utilities
"""

from typing import Dict, Any, List, Tuple, Union

# Global reports dictionary
reports: Dict[str, List[Tuple[Any, Dict[str, Any]]]] = {
    "updated": [],
    "appended": [],
    "unchanged": [],
    "error": [],
    "idx_error": [],
    "field_error": [],
}


def report(status: str, page_id: Any, update_msg: Dict[str, Any]) -> bool:
    """Add a report entry to the global reports dictionary"""
    if status in reports.keys():
        message = (page_id, update_msg)
        reports[status].append(message)
        message_out(status, message)
        return True
    else:
        return False


def report_out(report_dict: Dict[str, List[Tuple[Any, Dict[str, Any]]]]) -> None:
    """Print out a formatted report from the reports dictionary"""
    print("\n")
    for key in report_dict.keys():
        for page_data, message in report_dict[key]:
            print(key.upper())
            for item in page_data:
                print(f"\t{item}")
            print(f"\t{message}")
    print("=======================================================================")


def message_out(*args: Any) -> None:
    """Print output messages with proper formatting"""
    for item in args:
        print(item, end=" ")
    print()


def clear_reports() -> None:
    """Clear all report entries"""
    for key in reports.keys():
        reports[key].clear()


def get_report_summary() -> Dict[str, int]:
    """Get a summary of report counts"""
    summary = {}
    for key, items in reports.items():
        summary[key] = len(items)
    return summary
