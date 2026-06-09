"""
Docker-based command dispatch.
When Docker mode is active, commands execute inside containers.
Game-level commands (help, status, missions, quit, etc.) still run locally.
"""
from ui.console import console

# Commands that are handled by the Python game engine, NOT the container
GAME_COMMANDS = {
    "help", "status", "missions", "mission", "hint", "quit", "exit",
    "clear", "cls", "download",
    # Exploit/game mechanics — these have game logic
    "exploit", "crack", "osint", "phish",
}

# Commands that interact with both game state and container
HYBRID_COMMANDS = {
    "ssh", "disconnect", "nmap", "ping",
}


def is_game_command(cmd_name: str) -> bool:
    """Check if a command should be handled by the game engine."""
    return cmd_name in GAME_COMMANDS


def is_hybrid_command(cmd_name: str) -> bool:
    """Check if a command needs special game+docker handling."""
    return cmd_name in HYBRID_COMMANDS


def docker_exec_command(game, command: str, stdin_data: str | None = None) -> int:
    """Execute a command in the current Docker container.

    Returns exit code.
    """
    from engine.container import ContainerManager

    cm: ContainerManager = game.container_manager
    if not cm or not cm.is_docker_mode:
        return 127

    # Determine which container to use
    if game.is_on_localhost():
        host = cm.localhost
        user = game.player.handle
    else:
        ip = game.current_host.ip if game.current_host else None
        if not ip:
            return 127
        host = cm.get_host(ip)
        user = ""  # use container default user

    if not host:
        console.print_error(f"Container not available")
        return 1

    # Execute in container
    rc, stdout, stderr = host.exec(command, user=user, stdin_data=stdin_data)

    # Print output
    if stdout:
        # Don't add extra newline if stdout already ends with one
        if stdout.endswith("\n"):
            console.print(stdout, end="")
        else:
            console.print(stdout)

    if stderr:
        for line in stderr.strip().split("\n"):
            if line:
                console.print_error(line)

    return rc


def docker_dispatch(game, raw_input, stdin: str | None = None) -> int:
    """Main dispatch for Docker mode.

    Routes commands to either:
    1. Game engine (Python handlers) for game-specific commands
    2. Docker container for everything else
    """
    import shlex
    from commands.registry import dispatch as python_dispatch

    # Parse command name
    if isinstance(raw_input, list):
        tokens = raw_input
    else:
        try:
            tokens = shlex.split(raw_input)
        except ValueError:
            tokens = raw_input.strip().split()

    if not tokens:
        return 0

    cmd_name = tokens[0].lower()

    # Game commands → Python handlers
    if is_game_command(cmd_name):
        return python_dispatch(game, raw_input, stdin=stdin)

    # Hybrid commands → special handling
    if is_hybrid_command(cmd_name):
        return python_dispatch(game, raw_input, stdin=stdin)

    # Everything else → Docker container
    if isinstance(raw_input, list):
        # Reconstruct command string for docker exec
        import shlex as _shlex
        command = " ".join(_shlex.quote(t) for t in raw_input)
    else:
        command = raw_input

    return docker_exec_command(game, command, stdin_data=stdin)
