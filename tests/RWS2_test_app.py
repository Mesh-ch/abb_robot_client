"""
A textualize-based interactive CLI to run test functions from test_RWS2_POST.py.
"""
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static, ListView, ListItem
from textual.containers import Container
import importlib
import inspect


# Import the test module and get test functions
test_module = importlib.import_module("test_RWS2_POST")

from abb_robot_client.rws2 import RWS2

def get_test_functions():
    return [
        (name, func)
        for name, func in inspect.getmembers(test_module, inspect.isfunction)
        if name.startswith("test_")
    ]

class TestResult(Static):
    pass

class TestRWS2POST(App):
    CSS_PATH = None
    BINDINGS = [ ("q", "quit", "Quit") ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = RWS2()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            ListView(*[ListItem(Button(name, id=name)) for name, _ in get_test_functions()], id="test-list"),
            TestResult("Select a test to run.", id="result"),
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        test_name = event.button.id
        test_func = dict(get_test_functions())[test_name]
        result_widget = self.query_one("#result", TestResult)
        try:
            sig = inspect.signature(test_func)
            if len(sig.parameters) == 1:
                await asyncio.to_thread(test_func, self.client)
            else:
                await asyncio.to_thread(test_func)
            result_widget.update(f"[green]Test {test_name} passed![/green]")
        except Exception as e:
            result_widget.update(f"[red]Test {test_name} failed: {e}[/red]")

if __name__ == "__main__":
    app = TestRWS2POST()
    app.run()
