"""Textual JSON reviewer for mandatory human-in-the-loop approval."""
from __future__ import annotations

import importlib
import json
from typing import Any

from pydantic import BaseModel, ValidationError

try:
    _textual_app = importlib.import_module("textual.app")
    _textual_binding = importlib.import_module("textual.binding")
    _textual_widgets = importlib.import_module("textual.widgets")
    App = _textual_app.App
    ComposeResult = _textual_app.ComposeResult
    Binding = _textual_binding.Binding
    Footer = _textual_widgets.Footer
    Header = _textual_widgets.Header
    TextArea = _textual_widgets.TextArea
except Exception:  # pragma: no cover
    App = object
    ComposeResult = Any

    class Binding:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

    class _MissingWidget:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("textual is required for JSONReviewApp")

    Footer = Header = TextArea = _MissingWidget


class JSONReviewApp(App):  # type: ignore[misc, valid-type]
    BINDINGS = [
        Binding("ctrl+s", "approve", "保存并批准 (Approve)"),
        Binding("escape", "quit_app", "驳回并退出 (Reject)"),
    ]

    def __init__(self, model_class: type[BaseModel], initial_json_str: str) -> None:
        super().__init__()
        self.model_class = model_class
        self.initial_json_str = initial_json_str

    def compose(self) -> ComposeResult:  # type: ignore[valid-type]
        yield Header(show_clock=True)
        yield TextArea(self.initial_json_str, language="json", id="editor")
        yield Footer()

    def action_quit_app(self) -> None:
        self.exit(None)

    def action_approve(self) -> None:
        text = self.query_one("#editor", TextArea).text

        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            self.notify(f"JSON 语法错误: {error}", title="语法错误", severity="error", timeout=5)
            return

        try:
            validated_obj = self.model_class.model_validate_json(text)
        except ValidationError as error:
            self.notify(f"参数越界或缺失: {error}", title="校验失败", severity="error", timeout=6)
            return

        self.notify("校验通过，放行计算引擎。", severity="success", timeout=2)
        self.exit(validated_obj)


def require_human_approval_via_tui(model_class: type[BaseModel], initial_data: dict[str, Any]) -> BaseModel:
    json_str = json.dumps(initial_data, indent=2, ensure_ascii=False)
    app = JSONReviewApp(model_class=model_class, initial_json_str=json_str)
    result = app.run()
    if result is None:
        raise InterruptedError("人类专家驳回了参数注入，执行中止。")
    return result
