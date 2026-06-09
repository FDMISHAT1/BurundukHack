from io import StringIO
from rich.console import Console
from rich.theme import Theme
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

HACK_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "prompt": "green",
    "prompt.root": "bold red",
    "host": "bright_cyan",
    "port.open": "green",
    "port.closed": "red",
    "port.filtered": "yellow",
    "service": "bright_magenta",
    "vuln": "bold red on yellow",
    "mission": "bold bright_white",
    "objective.done": "strike green",
    "objective.pending": "yellow",
})


class HackConsole:
    def __init__(self):
        self.console = Console(theme=HACK_THEME, emoji=False)
        self._capture: StringIO | None = None
        self._capture_console: Console | None = None
        self._capture_stack: list[tuple[StringIO, Console]] = []
        # stderr routing: None=normal, "null"=suppress, "merge"=to stdout,
        # or a Console object to capture into a file
        self._stderr_mode = None
        self._stderr_capture: StringIO | None = None
        self._stderr_console: Console | None = None

    # --- capture mode for pipes / redirection ---

    def start_capture(self):
        # Push current capture onto stack for nesting
        if self._capture is not None:
            self._capture_stack.append((self._capture, self._capture_console))
        self._capture = StringIO()
        self._capture_console = Console(
            file=self._capture, highlight=False, no_color=True,
            theme=HACK_THEME, width=200, emoji=False,
        )

    def stop_capture(self) -> str:
        result = self._capture.getvalue() if self._capture else ""
        # Pop previous capture from stack
        if self._capture_stack:
            self._capture, self._capture_console = self._capture_stack.pop()
        else:
            self._capture = None
            self._capture_console = None
        return result

    # --- stderr redirection (2>, 2>/dev/null, 2>&1) ---

    def set_stderr_mode(self, mode):
        """mode: None | 'null' | 'merge' | 'capture'"""
        self._stderr_mode = mode
        if mode == "capture":
            self._stderr_capture = StringIO()
            self._stderr_console = Console(
                file=self._stderr_capture, highlight=False, no_color=True,
                theme=HACK_THEME, width=200, emoji=False,
            )
        else:
            self._stderr_capture = None
            self._stderr_console = None

    def reset_stderr(self) -> str:
        result = self._stderr_capture.getvalue() if self._stderr_capture else ""
        self._stderr_mode = None
        self._stderr_capture = None
        self._stderr_console = None
        return result

    @property
    def capturing(self) -> bool:
        return self._capture is not None

    @property
    def _out(self) -> Console:
        return self._capture_console if self._capture_console else self.console

    @property
    def _err(self) -> Console | None:
        """Return console for error output, or None if it should be dropped."""
        if self._stderr_mode == "null":
            return None
        if self._stderr_mode == "capture":
            return self._stderr_console
        # None or 'merge' -> follow stdout routing
        return self._out

    # --- output methods ---

    def print(self, *args, **kwargs):
        self._out.print(*args, **kwargs)

    def print_success(self, message: str):
        self._out.print(f"[success][+][/success] {message}")

    def print_error(self, message: str):
        err = self._err
        if err is not None:
            err.print(f"[error][-][/error] {message}")

    def print_warning(self, message: str):
        err = self._err
        if err is not None:
            err.print(f"[warning][!][/warning] {message}")

    def print_info(self, message: str):
        self._out.print(f"[info][*][/info] {message}")

    def print_panel(self, title: str, content: str, style: str = "green"):
        panel = Panel(content, title=title, border_style=style, padding=(1, 2))
        self._out.print(panel)

    def print_table(self, title: str, headers: list[str], rows: list[list[str]],
                     styles: list[str] | None = None):
        table = Table(title=title, border_style="green", header_style="bold bright_green")
        if styles is None:
            styles = ["cyan"] * len(headers)
        for header, style in zip(headers, styles):
            table.add_column(header, style=style)
        for row in rows:
            table.add_row(*row)
        self._out.print(table)

    def print_tree(self, title: str, items: dict):
        tree = Tree(f"[bold green]{title}[/bold green]")
        self._build_tree(tree, items)
        self._out.print(tree)

    def _build_tree(self, tree: Tree, items: dict):
        for key, value in items.items():
            if isinstance(value, dict):
                branch = tree.add(f"[cyan]{key}/[/cyan]")
                self._build_tree(branch, value)
            else:
                tree.add(f"[white]{key}[/white]")

    def input(self, prompt_text: str) -> str:
        return self.console.input(prompt_text)


console = HackConsole()
