"""Tests for the ALIFE tool registry and built-in tools."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools import build_tool_orchestrator
from tools.base import ToolParameter, ToolResult
from tools.builtin.get_time import GetTimeTool
from tools.builtin.open_application import OpenApplicationTool
from tools.builtin.open_website import OpenWebsiteTool
from tools.builtin.shutdown import SHUTDOWN_EXECUTION_ENABLED, perform_shutdown
from tools.builtin.system_info import SystemInfoTool
from tools.config import resolve_application, resolve_website
from tools.confirmation import ConfirmationManager
from tools.registry import ToolRegistry


class DummyTool:
    """Simple tool used for registry tests."""

    name = "dummy"
    description = "Dummy tool"
    parameters = [ToolParameter(name="value", description="A value")]

    def validate_arguments(self, arguments):
        if "value" not in arguments:
            raise ValueError("Missing value")
        return arguments

    def execute(self, arguments):
        return ToolResult(success=True, message=f"value={arguments['value']}")


class FailingTool:
    """Tool that raises during execution."""

    name = "failing"
    description = "Fails on purpose"
    parameters: list[ToolParameter] = []

    def validate_arguments(self, arguments):
        return arguments

    def execute(self, arguments):
        raise RuntimeError("boom")


class TestToolRegistry(unittest.TestCase):
    """Unit tests for ToolRegistry."""

    def test_register_and_lookup(self) -> None:
        registry = ToolRegistry()
        registry.register(DummyTool())

        tool = registry.get("dummy")

        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "dummy")

    def test_execute_unknown_tool(self) -> None:
        registry = ToolRegistry()

        result = registry.execute("missing", {})

        self.assertFalse(result.success)
        self.assertIn("don't know", result.message.lower())

    def test_execute_with_validation_error(self) -> None:
        registry = ToolRegistry()
        registry.register(DummyTool())

        result = registry.execute("dummy", {})

        self.assertFalse(result.success)

    def test_execute_with_exception(self) -> None:
        registry = ToolRegistry()
        registry.register(FailingTool())

        result = registry.execute("failing", {})

        self.assertFalse(result.success)
        self.assertIn("failed", result.message.lower())


class TestWebsiteTool(unittest.TestCase):
    """Unit tests for website opening."""

    @patch("tools.builtin.open_website.webbrowser.open", return_value=True)
    def test_open_known_website(self, mock_open) -> None:
        tool = OpenWebsiteTool()

        result = tool.execute({"site": "youtube"})

        self.assertTrue(result.success)
        mock_open.assert_called_once_with("https://www.youtube.com", new=2)

    def test_unknown_website(self) -> None:
        tool = OpenWebsiteTool()

        result = tool.execute({"site": "unknown-site"})

        self.assertFalse(result.success)


class TestApplicationTool(unittest.TestCase):
    """Unit tests for application launching."""

    def test_missing_application(self) -> None:
        tool = OpenApplicationTool()

        result = tool.execute({"app": "not-configured"})

        self.assertFalse(result.success)
        self.assertIn("configured yet", result.message)

    @patch("tools.builtin.open_application.subprocess.Popen")
    @patch.object(Path, "exists", return_value=True)
    def test_configured_application_launch(self, _exists, mock_popen) -> None:
        tool = OpenApplicationTool()

        result = tool.execute({"app": "vscode"})

        self.assertTrue(result.success)
        mock_popen.assert_called_once()
        self.assertFalse(mock_popen.call_args.kwargs.get("shell", False))


class TestTimeAndSystemTools(unittest.TestCase):
    """Unit tests for safe information tools."""

    def test_get_time(self) -> None:
        result = GetTimeTool().execute({})
        self.assertTrue(result.success)
        self.assertIn("It is", result.message)

    def test_system_info(self) -> None:
        result = SystemInfoTool().execute({})
        self.assertTrue(result.success)
        self.assertIn("Operating system", result.message)


class TestApplicationRegistry(unittest.TestCase):
    """Unit tests for configured application lookup."""

    def test_resolve_application(self) -> None:
        path = resolve_application("vscode")
        self.assertIsNotNone(path)


class TestConfirmationManager(unittest.TestCase):
    """Unit tests for destructive action confirmation."""

    def test_confirmation_flow(self) -> None:
        manager = ConfirmationManager()
        executed = {"value": False}

        def callback() -> str:
            executed["value"] = True
            return "Confirmed action executed."

        manager.set_pending(
            MagicMock(
                tool_name="request_shutdown",
                arguments={},
                prompt="Are you sure?",
                execute_callback=callback,
            )
        )

        prompt = manager.handle_response("maybe later")
        self.assertIn("yes", prompt.lower())
        self.assertFalse(executed["value"])

        result = manager.handle_response("yes")
        self.assertTrue(executed["value"])
        self.assertIn("executed", result.lower())


class TestToolOrchestrator(unittest.TestCase):
    """Unit tests for tool routing."""

    def setUp(self) -> None:
        self.provider = MagicMock()
        self.orchestrator, self.confirmation_manager = build_tool_orchestrator(self.provider)

    def test_rule_based_open_website(self) -> None:
        with patch("tools.builtin.open_website.webbrowser.open", return_value=True):
            result = self.orchestrator.try_handle("Open YouTube.")

        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.provider.generate.assert_not_called()

    def test_polite_open_youtube(self) -> None:
        with patch("tools.builtin.open_website.webbrowser.open", return_value=True):
            result = self.orchestrator.try_handle("Please open YouTube")

        self.assertIsNotNone(result)
        self.assertTrue(result.success)

    def test_rule_based_get_time(self) -> None:
        result = self.orchestrator.try_handle("What time is it?")

        self.assertIsNotNone(result)
        self.assertIn("It is", result.message)

    def test_voice_transcribed_open_youtube(self) -> None:
        with patch("tools.builtin.open_website.webbrowser.open", return_value=True):
            result = self.orchestrator.try_handle("open YouTube")

        self.assertIsNotNone(result)
        self.assertTrue(result.success)

    def test_multi_command_time_and_youtube(self) -> None:
        with patch("tools.builtin.open_website.webbrowser.open", return_value=True) as mock_open:
            result = self.orchestrator.try_handle("What time is it, then open YouTube")

        self.assertIsNotNone(result)
        self.assertIn("It is", result.message)
        self.assertIn("opened Youtube", result.message)
        mock_open.assert_called_once()

    def test_no_duplicate_tool_execution(self) -> None:
        with patch("tools.builtin.open_website.webbrowser.open", return_value=True) as mock_open:
            self.orchestrator.try_handle("Open YouTube and open YouTube")

        mock_open.assert_called_once()

    def test_unknown_request_falls_back_to_chat(self) -> None:
        self.provider.generate.return_value = '{"action":"chat"}'
        result = self.orchestrator.try_handle("Tell me a joke")
        self.assertIsNone(result)

    def test_invalid_model_json_falls_back_to_chat(self) -> None:
        self.provider.generate.return_value = "not json at all"
        result = self.orchestrator.try_handle("Do something mysterious")
        self.assertIsNone(result)

    def test_shutdown_requires_confirmation(self) -> None:
        result = self.orchestrator.try_handle("Shut down my laptop.")

        self.assertIsNotNone(result)
        self.assertTrue(result.requires_confirmation)
        self.assertTrue(self.confirmation_manager.has_pending())

    def test_shutdown_dry_run_never_calls_subprocess(self) -> None:
        with patch("subprocess.run") as mock_run, patch(
            "subprocess.Popen"
        ) as mock_popen:
            self.orchestrator.try_handle("Shut down my laptop.")
            response = self.confirmation_manager.handle_response("yes")

        self.assertFalse(SHUTDOWN_EXECUTION_ENABLED)
        self.assertIn("disabled", response.lower())
        mock_run.assert_not_called()
        mock_popen.assert_not_called()

    def test_perform_shutdown_never_invokes_os(self) -> None:
        with patch("subprocess.run") as mock_run, patch(
            "subprocess.Popen"
        ) as mock_popen, patch("os.system") as mock_system:
            message = perform_shutdown()

        self.assertIn("disabled", message.lower())
        mock_run.assert_not_called()
        mock_popen.assert_not_called()
        mock_system.assert_not_called()

    def test_sure_does_not_confirm_shutdown(self) -> None:
        self.orchestrator.try_handle("Shut down my laptop.")
        response = self.confirmation_manager.handle_response("sure")

        self.assertIn("yes", response.lower())
        self.assertTrue(self.confirmation_manager.has_pending())

    def test_common_commands_do_not_select_shutdown(self) -> None:
        safe_messages = [
            "Open YouTube.",
            "Open LeetCode.",
            "Open Google.",
            "Open GitHub.",
            "Open WhatsApp.",
            "Open VS Code.",
            "What time is it?",
            "Hello ALIFE.",
        ]
        self.provider.generate.return_value = '{"action":"chat"}'
        for message in safe_messages:
            with self.subTest(message=message):
                with patch("tools.builtin.shutdown.perform_shutdown") as mock_shutdown:
                    with patch("tools.builtin.open_website.webbrowser.open", return_value=True):
                        with patch("tools.builtin.open_application.subprocess.Popen"):
                            with patch("tools.builtin.open_application.Path.exists", return_value=True):
                                result = self.orchestrator.try_handle(message)
                    mock_shutdown.assert_not_called()
                if result is not None:
                    self.assertNotEqual(result.data.get("action"), "shutdown")


class TestWebsiteConfig(unittest.TestCase):
    """Unit tests for website resolution."""

    def test_resolve_website(self) -> None:
        self.assertEqual(resolve_website("YouTube"), "https://www.youtube.com")


if __name__ == "__main__":
    unittest.main()
