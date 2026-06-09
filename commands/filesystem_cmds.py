from commands.registry import register
from ui.console import console
from ui.lang import t


def _resolve_path(cwd: str, path: str) -> str:
    if path.startswith("/"):
        result = path
    else:
        if cwd == "/":
            result = "/" + path
        else:
            result = cwd.rstrip("/") + "/" + path

    parts = result.split("/")
    resolved = []
    for part in parts:
        if part == "" or part == ".":
            continue
        elif part == "..":
            if resolved:
                resolved.pop()
        else:
            resolved.append(part)
    return "/" + "/".join(resolved)


def _dir_exists(host, path: str) -> bool:
    """Check if path exists as a directory in the virtual filesystem."""
    if path == "/":
        return True
    prefix = path.rstrip("/") + "/"
    for filepath in host.files:
        if filepath.startswith(prefix):
            return True
    return False


@register("ls", "cmd.ls.help", required_tool="ls")
def handle_ls(game, args):
    if not game.current_host:
        console.print_error(t("fs.not_connected"))
        return

    host = game.current_host
    show_long = False
    show_all = False
    human = False
    recursive = False
    sort_size = False
    sort_time = False
    paths = []

    # Parse flags
    for arg in args:
        if arg.startswith("-"):
            fl = arg[1:]
            if "l" in fl: show_long = True
            if "a" in fl: show_all = True
            if "h" in fl: human = True
            if "R" in fl: recursive = True
            if "S" in fl: sort_size = True
            if "t" in fl: sort_time = True
        else:
            paths.append(arg)

    if not paths:
        paths = [host.cwd]

    rc = 0
    for p in paths:
        path = p if p.startswith("/") else _resolve_path(host.cwd, p)
        if len(paths) > 1:
            console.print(f"{path}:")

        if show_long:
            result = _ls_long(host, path, show_all, human, sort_size, sort_time)
        else:
            result = _ls_short(host, path, show_all)
        if result:
            rc = result

        if recursive:
            _ls_recursive(host, path, show_long, show_all, human, depth=0)

    return rc


def _ls_short(host, path: str, show_all: bool):
    items = host.list_files(path)
    if not items:
        if path in host.files:
            console.print(f"  [white]{path.split('/')[-1]}[/white]")
            return
        if not _dir_exists(host, path):
            console.print_error(f"ls: cannot access '{path}': No such file or directory")
            return 2
        console.print(f"[dim]  {t('fs.empty_dir')}[/dim]")
        return

    if show_all:
        console.print(f"  [bold cyan].[/bold cyan]  [bold cyan]..[/bold cyan]  ", end="")

    line_items = []
    for item in items:
        if item.startswith(".") and not show_all:
            continue
        if item.endswith("/"):
            line_items.append(f"[bold cyan]{item[:-1]}[/bold cyan]")
        else:
            line_items.append(f"[white]{item}[/white]")

    # When piped (capturing), output one item per line like real ls
    if console.capturing:
        plain_items = []
        for item in items:
            if item.startswith(".") and not show_all:
                continue
            plain_items.append(item.rstrip("/"))
        console.print("\n".join(plain_items))
    else:
        console.print("  ".join(line_items))


def _ls_recursive(host, path: str, show_long: bool, show_all: bool, human: bool, depth: int):
    """ls -R: list subdirectories recursively."""
    if depth > 10:
        return
    items = host.list_files(path)
    subdirs = [i.rstrip("/") for i in items if i.endswith("/")]
    for sd in sorted(subdirs):
        if sd.startswith(".") and not show_all:
            continue
        subpath = f"{path.rstrip('/')}/{sd}"
        console.print(f"\n{subpath}:")
        if show_long:
            _ls_long(host, subpath, show_all, human)
        else:
            _ls_short(host, subpath, show_all)
        _ls_recursive(host, subpath, show_long, show_all, human, depth + 1)


def _ls_long(host, path: str, show_all: bool, human: bool = False,
             sort_size: bool = False, sort_time: bool = False):
    detailed = host.list_files_detailed(path)
    if not detailed:
        if path in host.files:
            m = host.file_meta.get(path, {})
            content = host.files[path]
            console.print(f"{m.get('perms', '-rw-r--r--')} 1 {m.get('owner', 'root'):8s} "
                          f"{m.get('group', 'root'):8s} {len(content.encode()):>8d} "
                          f"{m.get('mtime', 'Nov 15 14:32')} {path.split('/')[-1]}")
            return
        if not _dir_exists(host, path):
            console.print_error(f"ls: cannot access '{path}': No such file or directory")
            return 2
        return

    # Sort entries
    if sort_size:
        detailed.sort(key=lambda e: e.get("size", 0), reverse=True)
    elif sort_time:
        detailed.sort(key=lambda e: e.get("mtime", ""), reverse=True)

    total = sum(d.get("size", 0) for d in detailed) // 1024
    console.print(f"total {total}")

    if show_all:
        console.print(f"drwxr-xr-x  2 root     root         4096 Nov 15 14:32 [bold cyan].[/bold cyan]")
        console.print(f"drwxr-xr-x  2 root     root         4096 Nov 15 14:32 [bold cyan]..[/bold cyan]")

    for entry in detailed:
        name = entry["name"]
        if name.startswith(".") and not show_all:
            continue

        perms = entry.get("perms", "-rw-r--r--")
        owner = entry.get("owner", "root")
        group = entry.get("group", "root")
        size = entry.get("size", 0)
        size_str = _human_size(size) if human else str(size)
        mtime = entry.get("mtime", "Nov 15 14:32")
        is_dir = entry.get("is_dir", False)

        if is_dir:
            display_name = f"[bold cyan]{name}[/bold cyan]"
        elif perms.startswith("-rwx") or "x" in perms[1:4]:
            display_name = f"[bold green]{name}[/bold green]"
        else:
            display_name = f"[white]{name}[/white]"

        nlinks = "2" if is_dir else "1"
        console.print(f"{perms} {nlinks:>2s} {owner:8s} {group:8s} {size_str:>8s} {mtime} {display_name}")


def _human_size(n: int) -> str:
    if n >= 1073741824:
        return f"{n/1073741824:.1f}G"
    if n >= 1048576:
        return f"{n/1048576:.1f}M"
    if n >= 1024:
        return f"{n/1024:.1f}K"
    return str(n)


@register("cd", "cmd.cd.help", required_tool="cd")
def handle_cd(game, args):
    if not game.current_host:
        console.print_error(t("fs.not_connected"))
        return

    host = game.current_host

    if not args:
        # cd without args goes to home
        user = host.get_current_user()
        if user == "root":
            host.cwd = "/root"
        else:
            host.cwd = f"/home/{user}"
        return

    path = args[0]

    # cd - → previous directory
    if path == "-":
        old = host.env.get("OLDPWD", host.cwd)
        host.env["OLDPWD"] = host.cwd
        host.cwd = old
        host.env["PWD"] = old
        console.print(old)
        return

    # Handle ~ expansion
    if path.startswith("~"):
        user = host.get_current_user()
        home = "/root" if user == "root" else f"/home/{user}"
        path = home + path[1:]

    new_path = _resolve_path(host.cwd, path)

    # Verify directory exists
    prefix = new_path.rstrip("/") + "/"
    if new_path == "/":
        prefix = "/"

    exists = any(f.startswith(prefix) or f == new_path for f in host.files)

    if new_path == "/":
        exists = True

    if exists:
        host.env["OLDPWD"] = host.cwd
        host.cwd = new_path
        host.env["PWD"] = new_path
    else:
        console.print_error(t("fs.no_such_dir", path=args[0]))


@register("cat", "cmd.cat.help", required_tool="cat")
def handle_cat(game, args):
    if not game.current_host:
        console.print_error(t("fs.not_connected"))
        return

    host = game.current_host
    show_numbers = "-n" in args
    flags = [a for a in args if a.startswith("-")]
    file_args = [a for a in args if not a.startswith("-")]

    # No file args — read from stdin (pipe)
    if not file_args:
        if game.stdin:
            content = game.stdin
            if show_numbers:
                for i, line in enumerate(content.split("\n"), 1):
                    console.print(f"{i:>6d}\t{line}")
            else:
                console.print(content, end="" if content.endswith("\n") else "\n")
            return
        console.print_error(t("fs.cat_usage"))
        return

    # Process each file
    for fname in file_args:
        filepath = fname if fname.startswith("/") else _resolve_path(host.cwd, fname)

        # Special device files
        if filepath == "/dev/null":
            continue  # produces no output
        if filepath == "/dev/zero":
            console.print("\x00" * 256)  # limited output
            continue
        if filepath == "/dev/urandom" or filepath == "/dev/random":
            import random as _rnd
            data = bytes(_rnd.randint(0, 255) for _ in range(256))
            console.print("".join(f"\\x{b:02x}" for b in data))
            continue

        if filepath not in host.files:
            console.print_error(t("fs.no_such_file", path=filepath))
            continue

        content = host.files[filepath]

        if content.startswith("[ELF ") or content.startswith("[binary") or content == "[device node]":
            console.print_error(f"cat: {filepath}: cannot display binary file")
            continue

        if "[REQUIRES ROOT]" in content and host.access_level != "root":
            console.print_error(t("fs.permission_denied", path=filepath))
            continue
        if "[PERMISSION DENIED" in content and host.access_level != "root":
            console.print_error(t("fs.permission_denied", path=filepath))
            continue

        # Shadow file needs root
        if "/shadow" in filepath and host.access_level != "root":
            console.print_error(t("fs.permission_denied", path=filepath))
            continue

        if show_numbers:
            for i, line in enumerate(content.split("\n"), 1):
                console.print(f"{i:>6d}\t{line}")
        else:
            console.print(content, end="" if content.endswith("\n") else "\n")

        # Track file read
        file_key = f"{host.ip}:{filepath}"
        game.player.files_read.add(file_key)
        game.check_objective("read_file", ip=host.ip, file=filepath)

    # Auto-discover credentials
    _scan_for_credentials(game, content, host.ip)


def _scan_for_credentials(game, content: str, source_ip: str):
    import re

    patterns = [
        r'(?:password|pass|passwd|pwd|db_pass)\s*[=:]\s*(\S+)',
        r'(?:user|username|login|db_user)\s*[=:]\s*(\S+)',
    ]

    users_found = []
    passwords_found = []

    for line in content.split("\n"):
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                value = match.group(1).strip('"\'')
                if "user" in pattern:
                    users_found.append(value)
                else:
                    passwords_found.append(value)

    ip_pattern = r'(?:host|server|db_host)\s*[=:]\s*([\d.]+)'
    hosts_found = []
    for line in content.split("\n"):
        match = re.search(ip_pattern, line, re.IGNORECASE)
        if match:
            hosts_found.append(match.group(1))

    if users_found and passwords_found:
        target_host = hosts_found[0] if hosts_found else source_ip
        for user, passwd in zip(users_found, passwords_found):
            game.player.add_credential(user, passwd, target_host)
            console.print_info(t("fs.creds_discovered",
                                  user=f"[bold]{user}[/bold]",
                                  password=f"[bold]{passwd}[/bold]",
                                  host=target_host))


@register("download", "cmd.download.help", required_tool="download")
def handle_download(game, args):
    if not game.current_host:
        console.print_error(t("fs.not_connected"))
        return

    if not args:
        console.print_error(t("fs.download_usage"))
        return

    host = game.current_host
    filepath = args[0]

    if not filepath.startswith("/"):
        filepath = _resolve_path(host.cwd, filepath)

    if filepath not in host.files:
        console.print_error(t("fs.download_no_file", path=filepath))
        return

    content = host.files[filepath]
    if "[REQUIRES ROOT]" in content and host.access_level != "root":
        console.print_error(t("fs.download_denied", path=filepath))
        return

    from ui.animations import fake_progress
    fake_progress(t("fs.downloading", path=filepath), seconds=2.0)

    file_key = f"{host.ip}:{filepath}"
    game.player.files_downloaded.add(file_key)

    console.print_success(t("fs.downloaded", path=filepath))
    console.print(f"[dim]  {t('fs.saved_to', filename=filepath.split('/')[-1])}[/dim]")

    game.check_objective("download_file", ip=host.ip, file=filepath)
