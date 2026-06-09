from commands.registry import register
from commands.filesystem_cmds import _resolve_path
from ui.console import console
from ui.lang import t


def _require_host(game) -> bool:
    if not game.current_host:
        console.print_error(t("fs.not_connected"))
        return False
    return True


def _track_file(host, path: str, content: str):
    """Write file and track it for saving."""
    host.files[path] = content
    host.user_files[path] = content
    # Add default metadata
    user = host.get_current_user()
    host.file_meta[path] = {
        "perms": "-rw-r--r--", "owner": user, "group": user,
        "mtime": "Nov 15 14:35",
    }


def _track_delete(host, path: str):
    """Delete file and mark deletion for saving."""
    host.files.pop(path, None)
    host.file_meta.pop(path, None)
    host.user_files[path] = "__DELETED__"


@register("touch", "cmd.touch.help", required_tool="touch")
def handle_touch(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: touch FILE...")
        console.print("Update the access and modification times of each FILE to the current time.")
        console.print("A FILE that does not exist is created empty.")
        return
    if not _require_host(game):
        return
    if not args:
        console.print_error("touch: missing file operand")
        return

    host = game.current_host
    for name in args:
        path = name if name.startswith("/") else _resolve_path(host.cwd, name)
        if path not in host.files:
            _track_file(host, path, "")


@register("mkdir", "cmd.mkdir.help", required_tool="mkdir")
def handle_mkdir(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: mkdir [OPTION] DIRECTORY...\n")
        console.print("  mkdir dir          create directory")
        console.print("  mkdir -p a/b/c     create parent directories as needed")
        return
    if not _require_host(game):
        return
    if not args or (len(args) == 1 and args[0] == "-p"):
        console.print_error("mkdir: missing operand")
        return

    host = game.current_host
    create_parents = "-p" in args
    dirs = [a for a in args if a != "-p"]

    for name in dirs:
        path = name if name.startswith("/") else _resolve_path(host.cwd, name)
        # Check if dir already exists
        prefix = path.rstrip("/") + "/"
        exists = any(f.startswith(prefix) for f in host.files)
        if exists and not create_parents:
            console.print_error(f"mkdir: cannot create directory '{name}': File exists")
            continue
        # Create dir by adding a .keep marker
        _track_file(host, f"{path}/.keep", "")


@register("rm", "cmd.rm.help", required_tool="rm")
def handle_rm(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: rm [OPTION]... FILE...\n")
        console.print("  rm file            remove file")
        console.print("  rm -r dir          remove directory and its contents")
        console.print("  rm -f file         force remove without confirmation")
        return
    if not _require_host(game):
        return
    if not args or all(a.startswith("-") for a in args):
        console.print_error("rm: missing operand")
        return

    host = game.current_host
    recursive = "-r" in args or "-rf" in args or "-fr" in args
    files = [a for a in args if not a.startswith("-")]

    for name in files:
        path = name if name.startswith("/") else _resolve_path(host.cwd, name)

        if path in host.files:
            _track_delete(host, path)
            continue

        # Maybe it's a directory
        prefix = path.rstrip("/") + "/"
        children = [f for f in host.files if f.startswith(prefix)]
        if children:
            if not recursive:
                console.print_error(f"rm: cannot remove '{name}': Is a directory")
                continue
            for child in children:
                _track_delete(host, child)
            continue

        console.print_error(f"rm: cannot remove '{name}': No such file or directory")


@register("cp", "cmd.cp.help", required_tool="cp")
def handle_cp(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: cp [OPTION] SOURCE DEST\n")
        console.print("  cp file1 file2     copy file1 to file2")
        console.print("  cp -r dir1 dir2    copy directory recursively")
        return
    if not _require_host(game):
        return
    clean = [a for a in args if not a.startswith("-")]
    if len(clean) < 2:
        console.print_error("cp: missing destination file operand")
        return

    host = game.current_host
    src = clean[0] if clean[0].startswith("/") else _resolve_path(host.cwd, clean[0])
    dst = clean[1] if clean[1].startswith("/") else _resolve_path(host.cwd, clean[1])

    if src not in host.files:
        console.print_error(f"cp: cannot stat '{clean[0]}': No such file or directory")
        return

    _track_file(host, dst, host.files[src])


@register("mv", "cmd.mv.help", required_tool="mv")
def handle_mv(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: mv [OPTION] SOURCE DEST\n")
        console.print("  mv file1 file2     rename file1 to file2")
        console.print("  mv file dir/       move file into directory")
        return
    if not _require_host(game):
        return
    clean = [a for a in args if not a.startswith("-")]
    if len(clean) < 2:
        console.print_error("mv: missing destination file operand")
        return

    host = game.current_host
    src = clean[0] if clean[0].startswith("/") else _resolve_path(host.cwd, clean[0])
    dst = clean[1] if clean[1].startswith("/") else _resolve_path(host.cwd, clean[1])

    if src not in host.files:
        console.print_error(f"mv: cannot stat '{clean[0]}': No such file or directory")
        return

    _track_file(host, dst, host.files[src])
    _track_delete(host, src)


@register("nano", "cmd.nano.help", required_tool="nano")
def handle_nano(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: nano [FILE]\n")
        console.print("  nano file.txt      open file for editing")
        console.print("  nano               open new empty buffer")
        console.print("\nIn editor: type text line by line.")
        console.print("  Type :w   to save")
        console.print("  Type :q   to quit")
        console.print("  Type :wq  to save and quit")
        return
    if not _require_host(game):
        return

    host = game.current_host

    if args:
        name = args[0]
        filepath = name if name.startswith("/") else _resolve_path(host.cwd, name)
    else:
        filepath = _resolve_path(host.cwd, "untitled.txt")

    # Load existing content
    existing = host.files.get(filepath, "")
    if existing.startswith("[ELF ") or existing.startswith("[binary") or existing == "[device node]":
        console.print_error(f"nano: {filepath}: binary file — cannot edit")
        return

    console.print()
    console.print(f"[bold green]  GNU nano 5.4[/bold green]{'':20s}[bold green]{filepath}[/bold green]")
    console.print(f"[dim]{'─' * 70}[/dim]")

    if existing:
        for line in existing.split("\n"):
            console.print(f"[dim]  {line}[/dim]")
        console.print(f"[dim]{'─' * 70}[/dim]")

    console.print(f"[dim]  Enter text (one line at a time). Commands:[/dim]")
    console.print(f"[dim]  :w = save  |  :q = quit  |  :wq = save & quit[/dim]")
    console.print(f"[dim]{'─' * 70}[/dim]")

    lines = existing.split("\n") if existing else []
    modified = False

    while True:
        try:
            line = console.input("[green]> [/green]")
        except (EOFError, KeyboardInterrupt):
            break

        cmd = line.strip()
        if cmd == ":wq":
            content = "\n".join(lines)
            _track_file(host, filepath, content)
            console.print(f"[dim]  [ Wrote {len(lines)} lines to {filepath} ][/dim]")
            modified = True
            break
        elif cmd == ":w":
            content = "\n".join(lines)
            _track_file(host, filepath, content)
            console.print(f"[dim]  [ Wrote {len(lines)} lines to {filepath} ][/dim]")
            modified = True
            continue
        elif cmd == ":q":
            if modified:
                console.print(f"[dim]  [ Quit ][/dim]")
            else:
                console.print(f"[dim]  [ Quit without saving ][/dim]")
            break
        else:
            lines.append(line)

    console.print()


@register("vi", "cmd.vi.help", required_tool="vi")
def handle_vi(game, args):
    handle_nano(game, args)
