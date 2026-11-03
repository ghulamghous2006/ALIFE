"""ALIFE application entry point."""

import logging
import sys

from rich.console import Console

from brain.conversation.conversation_manager import ConversationManager
from brain.providers.ollama_provider import (
    DEFAULT_HOST,
    OllamaConnectionError,
    OllamaProvider,
    OllamaProviderError,
)
from core.config import load_config
from core.instance import InstanceLock
from core.logging import setup_logging
from core.ollama_health import wait_for_ollama
from memory.database import Database
from memory.memory_manager import MemoryManager
from tools import build_tool_orchestrator
from voice import VoiceManager
from voice.exceptions import VoiceError

BANNER = """\
====================================
          ALIFE v0.4
===================================="""

logger = logging.getLogger(__name__)


def configure_terminal() -> None:
    """Configure stdout for UTF-8 output on supported platforms."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError) as exc:
            logger.debug("Could not reconfigure stdout encoding: %s", exc)


def display_alife_message(console: Console, message: str) -> None:
    """Display an ALIFE response in the terminal."""
    console.print("[green]ALIFE:[/green]")
    console.print(f"[green]{message}[/green]")


def run_voice_interaction(console: Console, voice_manager: VoiceManager) -> None:
    """Run one push-to-talk voice interaction cycle."""
    display_alife_message(console, "Listening...")
    try:
        result = voice_manager.listen_and_respond()
        if result.heard:
            display_alife_message(console, f'I heard: "{result.heard}"')
            console.print()
        display_alife_message(console, result.response)
    except VoiceError as exc:
        logger.error("Voice interaction failed: %s", exc)
        console.print(f"[red]Error:[/red] {exc}")


def run_chat_loop(
    console: Console,
    conversation: ConversationManager,
    voice_manager: VoiceManager | None,
) -> None:
    """Run the interactive terminal chat loop."""
    while True:
        try:
            console.print("[cyan]You:[/cyan]")
            user_input = console.input("").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            logger.info("Chat session interrupted by user")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "/exit"}:
            logger.info("User requested exit")
            break

        console.print(f"[cyan]{user_input}[/cyan]\n")

        try:
            if user_input.lower() == "/voice":
                if voice_manager is None:
                    console.print("[red]Error:[/red] Voice mode is unavailable.")
                else:
                    run_voice_interaction(console, voice_manager)
            else:
                command_response = conversation.handle_command(user_input)
                if command_response is not None:
                    display_alife_message(console, command_response)
                else:
                    response = conversation.generate_response(user_input)
                    display_alife_message(console, response)
        except OllamaProviderError as exc:
            logger.error("Provider error: %s", exc)
            console.print(f"[red]Error:[/red] {exc}")
        except ValueError as exc:
            logger.warning("Invalid input: %s", exc)
            console.print(f"[red]Error:[/red] {exc}")
        except UnicodeEncodeError as exc:
            logger.error("Terminal encoding error: %s", exc)
            console.print("[red]Error:[/red] Unable to display response (encoding issue)")
        except Exception as exc:
            logger.exception("Unexpected chat-loop error: %s", exc)
            console.print(f"[red]Error:[/red] {exc}")

        console.print()


def main() -> int:
    """Initialize and run the ALIFE application."""
    config = load_config()
    setup_logging(level=config.log_level)
    configure_terminal()

    logger.info("ALIFE starting (env=%s)", config.env)

    console = Console()
    instance_lock = InstanceLock()
    if not instance_lock.acquire():
        console.print("[red]Error:[/red] ALIFE is already running.")
        return 1

    try:
        if not wait_for_ollama(DEFAULT_HOST):
            console.print(
                "[red]Error:[/red] Ollama is not ready. "
                "Start Ollama, then run `ollama run qwen3:4b` once if needed."
            )
            return 1

        database = Database()
        memory_manager = MemoryManager(database)
        try:
            provider = OllamaProvider()
        except OllamaConnectionError as exc:
            logger.error("Ollama provider initialization failed: %s", exc)
            console.print(f"[red]Error:[/red] {exc}")
            return 1

        tool_orchestrator, confirmation_manager = build_tool_orchestrator(provider)
        conversation = ConversationManager(
            provider,
            memory_manager,
            database,
            tool_orchestrator=tool_orchestrator,
            confirmation_manager=confirmation_manager,
        )

        try:
            voice_manager: VoiceManager | None = VoiceManager(conversation)
        except Exception as exc:
            logger.warning("Voice manager unavailable: %s", exc)
            voice_manager = None

        console.print(BANNER)
        console.print()
        logger.info("Terminal chat interface ready (model=%s)", provider.model)

        run_chat_loop(console, conversation, voice_manager)

        logger.info("ALIFE shutting down")
        return 0
    finally:
        instance_lock.release()


if __name__ == "__main__":
    sys.exit(main())
