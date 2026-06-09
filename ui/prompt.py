"""
Game prompt powered by prompt_toolkit.
Provides: arrow keys, history (up/down), Ctrl+A/E/K/U/W/D/C/L/R,
tab completion for commands & paths.
Falls back to plain input() when stdin is not a TTY.
"""
import sys
import os
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings


_session: PromptSession | None = None
_command_names: list[str] = []
_game_ref = None
_is_tty: bool = False
_history_list: list[str] = []  # for !! and !N access


class GameCompleter(Completer):
    """Tab-complete command names (first word) and file paths (subsequent words)."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        word_before = document.get_word_before_cursor(WORD=True)

        if len(words) <= 1 and not text.endswith(" "):
            for cmd in _command_names:
                if cmd.startswith(word_before):
                    yield Completion(cmd, start_position=-len(word_before))
            # Also complete aliases
            if _game_ref and hasattr(_game_ref, 'aliases'):
                for alias_name in _game_ref.aliases:
                    if alias_name.startswith(word_before) and alias_name not in _command_names:
                        yield Completion(alias_name, start_position=-len(word_before))
        else:
            if _game_ref and _game_ref.current_host:
                yield from _complete_path(_game_ref.current_host, word_before)


def _complete_path(host, partial: str):
    from commands.filesystem_cmds import _resolve_path

    if partial.startswith("/"):
        base = partial
    elif partial:
        base = _resolve_path(host.cwd, partial)
    else:
        base = host.cwd

    if "/" in partial and not partial.endswith("/"):
        dir_part = base.rsplit("/", 1)[0] or "/"
        name_part = partial.rsplit("/", 1)[-1]
    elif partial.endswith("/"):
        dir_part = base.rstrip("/") or "/"
        name_part = ""
    else:
        dir_part = host.cwd
        name_part = partial

    items = host.list_files(dir_part)
    for item in items:
        clean = item.rstrip("/")
        if clean.startswith(name_part):
            yield Completion(
                item if item.endswith("/") else clean,
                start_position=-len(name_part),
            )


def _make_keybindings():
    """Custom key bindings: Ctrl+L = clear screen."""
    kb = KeyBindings()

    @kb.add("c-l")
    def _(event):
        os.system("clear" if os.name != "nt" else "cls")
        event.app.renderer.reset()
        event.app.invalidate()

    return kb


def init_prompt(command_names: list[str], game=None):
    global _session, _command_names, _game_ref, _is_tty
    _command_names = sorted(command_names)
    _game_ref = game
    _is_tty = sys.stdin.isatty()
    if _is_tty:
        _session = PromptSession(
            history=InMemoryHistory(),
            completer=GameCompleter(),
            complete_while_typing=False,
            key_bindings=_make_keybindings(),
            enable_history_search=True,  # Ctrl+R search
        )


def prompt_input(prompt_ansi: str) -> str:
    if not _is_tty or _session is None:
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', prompt_ansi)
        return input(clean)

    raw = _session.prompt(ANSI(prompt_ansi))

    # Track history for !! and !N
    if raw.strip():
        _history_list.append(raw.strip())

    return raw


def expand_history(raw: str) -> str:
    """Expand !! !N !$ ^old^new before processing."""
    if not _history_list:
        return raw

    # !! → last command
    if "!!" in raw:
        raw = raw.replace("!!", _history_list[-1] if _history_list else "")

    # !$ → last argument of last command
    if "!$" in raw and _history_list:
        last_args = _history_list[-1].split()
        raw = raw.replace("!$", last_args[-1] if last_args else "")

    # !N → command N from history
    import re
    def replace_bang_n(m):
        n = int(m.group(1))
        if 1 <= n <= len(_history_list):
            return _history_list[n - 1]
        return m.group(0)
    raw = re.sub(r'!(\d+)', replace_bang_n, raw)

    # ^old^new → repeat last command with substitution
    m = re.match(r'\^(.+?)\^(.+?)(?:\^)?$', raw)
    if m and _history_list:
        raw = _history_list[-1].replace(m.group(1), m.group(2))

    return raw


def get_history_list() -> list[str]:
    return _history_list
