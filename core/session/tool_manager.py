"""
Tool management for filtering and providing tools based on session mode.
"""

from typing import Any

from ..base_tools import get_base_tools, get_user_tools
from ..logger import logger


class ToolManager:
    """Manages tool availability based on session mode."""

    def __init__(self):
        self._base_tools = None
        self._user_tools = None

    def get_tools(self, mode: str) -> list[dict[str, Any]]:
        """Get tools for given mode (guest/user)."""
        # Lazy load tools
        if self._base_tools is None:
            self._base_tools = get_base_tools()
        if self._user_tools is None:
            self._user_tools = get_user_tools()

        if mode == "guest":
            return self._base_tools
        if mode == "user":
            return self._base_tools + self._user_tools
        logger.warning(f"Unknown mode: {mode}, using base tools")
        return self._base_tools

    def refresh_tools(self):
        """Refresh tool definitions (e.g., after song list changes)."""
        self._base_tools = get_base_tools()
        self._user_tools = get_user_tools()


# Singleton instance
tool_manager = ToolManager()
