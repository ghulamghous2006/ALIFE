"""Open approved websites in the default browser."""

import logging
import webbrowser
from typing import Any

from tools.base import BaseTool, ToolParameter, ToolResult
from tools.config import resolve_website

logger = logging.getLogger(__name__)


class OpenWebsiteTool(BaseTool):
    """Open a configured website using the default browser."""

    @property
    def name(self) -> str:
        return "open_website"

    @property
    def description(self) -> str:
        return "Open an approved website in the default browser"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="site",
                description="Website name such as youtube, leetcode, google, or github",
            )
        ]

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        site = str(arguments["site"])
        url = resolve_website(site)
        if url is None:
            return ToolResult(
                success=False,
                message=f"I don't have the website '{site}' configured yet.",
            )

        try:
            opened = webbrowser.open(url, new=2)
        except Exception as exc:
            logger.error("Failed to open website url=%s: %s", url, exc)
            return ToolResult(
                success=False,
                message=f"I couldn't open {site.title()}: {exc}",
                data={"url": url},
            )

        if not opened:
            logger.warning("webbrowser.open returned False for url=%s", url)
            return ToolResult(
                success=False,
                message=(
                    f"I tried to open {site.title()}, but the browser did not confirm "
                    "that it launched."
                ),
                data={"url": url},
            )

        return ToolResult(
            success=True,
            message=f"Done. I've opened {site.title()}.",
            data={"url": url},
        )
