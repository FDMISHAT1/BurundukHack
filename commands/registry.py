import shlex
from typing import Callable, TYPE_CHECKING
from ui.console import console
from ui.lang import t

if TYPE_CHECKING:
    from engine.game import Game

# (handler, help_key, required_tool)
COMMANDS: dict[str, tuple[Callable, str, str | None]] = {}


def register(name: str, help_key: str, required_tool: str | None = None):
    def decorator(func: Callable):
        COMMANDS[name] = (func, help_key, required_tool or name)
        return func
    return decorator


def dispatch(game: "Game", raw_input, stdin: str | None = None) -> int:
    """Execute a single simple command. Returns its exit code.

    raw_input may be a raw string (will be shlex-split) or an already
    tokenised list of arguments (used by the shell layer after expansion).
    stdin is piped/redirected input made available to stdin-aware commands.
    """
    if isinstance(raw_input, str):
        try:
            tokens = shlex.split(raw_input)
        except ValueError:
            tokens = raw_input.strip().split()
    else:
        tokens = list(raw_input)

    if not tokens:
        return 0

    # Bash-style comments
    if tokens[0].startswith("#"):
        return 0

    cmd_name = tokens[0].lower()
    args = tokens[1:]

    if cmd_name not in COMMANDS:
        console.print_error(t("registry.cmd_not_found", cmd=cmd_name))
        game.last_exit_code = 127
        return 127

    handler, help_key, required_tool = COMMANDS[cmd_name]

    if required_tool and required_tool not in game.player.tools_unlocked:
        console.print_error(t("registry.tool_locked", cmd=cmd_name))
        game.last_exit_code = 127
        return 127

    game.stdin = stdin
    try:
        rc = handler(game, args)
    finally:
        game.stdin = None
    rc = rc if isinstance(rc, int) else 0
    game.last_exit_code = rc
    return rc
