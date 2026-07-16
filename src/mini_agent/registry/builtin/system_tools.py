"""
registry/builtin/system_tools.py
------------------------------------
Date/time and system-info tools.
"""

import datetime
import os

from ..tools import Tool


def get_current_datetime() -> str:
    """Returns the current date and time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_current_working_directory() -> str:
    """Returns the current working directory path."""
    return os.getcwd()


SYSTEM_TOOLS = [
    Tool(name="get_current_datetime", description="Returns the current date/time", func=get_current_datetime),
    Tool(name="get_current_working_directory", description="Returns the current working directory", func=get_current_working_directory),
]
