"""Extra Linux commands: rmdir, readlink, chgrp, groupadd, paste, hexdump,
shred, w, who, last, users, basename, dirname, realpath, mktemp, yes, true, false,
tac, comm, expand, unexpand, nohup, xdg-open, clear (improved), reset."""
import random
import os
from commands.registry import register
from commands.linux_cmds import _require_host, _wants_help, _get_input
from commands.filesystem_cmds import _resolve_path
from ui.console import console


# ── true / false ──

@register("true", "cmd.true.help", required_tool="true")
def handle_true(game, args):
    return 0

@register("false", "cmd.false.help", required_tool="false")
def handle_false(game, args):
    return 1


# ── basename / dirname / realpath ──

@register("basename", "cmd.basename.help", required_tool="basename")
def handle_basename(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: basename NAME [SUFFIX]\n  basename /etc/passwd  →  passwd")
        return
    name = args[0]
    suffix = args[1] if len(args) > 1 else ""
    result = name.rstrip("/").rsplit("/", 1)[-1]
    if suffix and result.endswith(suffix):
        result = result[:-len(suffix)]
    console.print(result)

@register("dirname", "cmd.dirname.help", required_tool="dirname")
def handle_dirname(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: dirname NAME\n  dirname /etc/passwd  →  /etc")
        return
    path = args[0]
    result = path.rsplit("/", 1)[0] if "/" in path else "."
    console.print(result or "/")

@register("realpath", "cmd.realpath.help", required_tool="realpath")
def handle_realpath(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: realpath FILE\n  realpath ./file  →  /full/path/file")
        return
    if not _require_host(game): return
    path = args[0] if args[0].startswith("/") else _resolve_path(game.current_host.cwd, args[0])
    console.print(path)


# ── rmdir ──

@register("rmdir", "cmd.rmdir.help", required_tool="rmdir")
def handle_rmdir(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: rmdir DIRECTORY...\n  rmdir dir     remove empty directory\n  rmdir -p a/b  remove parents too")
        return
    if not _require_host(game): return
    host = game.current_host
    for d in args:
        if d.startswith("-"): continue
        dp = d if d.startswith("/") else _resolve_path(host.cwd, d)
        prefix = dp.rstrip("/") + "/"
        children = [f for f in host.files if f.startswith(prefix) and f != prefix + ".keep"]
        if children:
            console.print_error(f"rmdir: failed to remove '{d}': Directory not empty")
        else:
            # Remove .keep marker
            host.files.pop(prefix + ".keep", None)
            host.user_files[prefix + ".keep"] = "__DELETED__"


# ── readlink ──

@register("readlink", "cmd.readlink.help", required_tool="readlink")
def handle_readlink(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: readlink [OPTIONS] FILE\n  readlink link    show symlink target\n  readlink -f file resolve all symlinks")
        return
    if not _require_host(game): return
    path = args[-1] if not args[-1].startswith("-") else None
    if not path:
        console.print_error("readlink: missing operand")
        return
    fp = path if path.startswith("/") else _resolve_path(game.current_host.cwd, path)
    m = game.current_host.file_meta.get(fp, {})
    if m.get("perms", "").startswith("l"):
        console.print(fp)  # symlinks store target content
    else:
        console.print(fp)


# ── chgrp / groupadd / groupdel ──

@register("chgrp", "cmd.chgrp.help", required_tool="chgrp")
def handle_chgrp(game, args):
    if _wants_help(args) or len(args) < 2:
        console.print("Usage: chgrp [OPTION] GROUP FILE...\n  chgrp staff file\n  chgrp -R staff dir/")
        return
    if not _require_host(game): return
    host = game.current_host
    group = args[0] if not args[0].startswith("-") else args[1]
    files = [a for a in args if not a.startswith("-") and a != group]
    for f in files:
        fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
        if fp in host.file_meta:
            host.file_meta[fp]["group"] = group

@register("groupadd", "cmd.groupadd.help", required_tool="groupadd")
def handle_groupadd(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: groupadd GROUP")
        return
    if not _require_host(game): return
    if game.current_host.access_level != "root":
        console.print_error("groupadd: Permission denied")
        return 1
    name = args[-1]
    gf = game.current_host.files.get("/etc/group", "")
    gid = 1000 + gf.count("\n")
    game.current_host.files["/etc/group"] = gf + f"\n{name}:x:{gid}:"
    game.current_host.user_files["/etc/group"] = game.current_host.files["/etc/group"]
    console.print(f"[dim]groupadd: group '{name}' added (gid={gid})[/dim]")

@register("groupdel", "cmd.groupdel.help", required_tool="groupdel")
def handle_groupdel(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: groupdel GROUP")
        return
    console.print(f"[dim]groupdel: group '{args[-1]}' removed[/dim]")


# ── paste ──

@register("paste", "cmd.paste.help", required_tool="paste")
def handle_paste(game, args):
    if _wants_help(args):
        console.print("Usage: paste [OPTIONS] FILE...\n  paste file1 file2  merge side-by-side\n  paste -d: file1 file2  use : delimiter\n  paste -s file   serial (one file per line)")
        return
    if not _require_host(game): return
    delim = "\t"
    serial = "-s" in args
    if "-d" in args:
        idx = args.index("-d")
        if idx + 1 < len(args): delim = args[idx + 1]
    for a in args:
        if a.startswith("-d") and len(a) > 2: delim = a[2:]

    file_args = [a for a in args if not a.startswith("-") and a != delim]
    if not file_args:
        console.print_error("paste: missing operand")
        return
    host = game.current_host
    file_lines = []
    for f in file_args:
        fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
        content = host.files.get(fp, "")
        file_lines.append(content.split("\n"))

    if serial:
        for lines in file_lines:
            console.print(delim.join(lines))
    else:
        max_len = max(len(fl) for fl in file_lines)
        for i in range(max_len):
            parts = [fl[i] if i < len(fl) else "" for fl in file_lines]
            console.print(delim.join(parts))


# ── hexdump ──

@register("hexdump", "cmd.hexdump.help", required_tool="hexdump")
def handle_hexdump(game, args):
    if _wants_help(args):
        console.print("Usage: hexdump [OPTIONS] FILE\n  hexdump -C file   canonical hex+ASCII dump")
        return
    content = _get_input(game, args, "hexdump")
    if content is None: return
    data = content.encode()[:256]
    canonical = "-C" in args
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hex1 = " ".join(f"{b:02x}" for b in chunk[:8])
        hex2 = " ".join(f"{b:02x}" for b in chunk[8:])
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        if canonical:
            console.print(f"{off:08x}  {hex1:<24s} {hex2:<24s} |{asc}|")
        else:
            console.print(f"{off:08x}  {hex1} {hex2}")


# ── shred ──

@register("shred", "cmd.shred.help", required_tool="shred")
def handle_shred(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: shred [OPTIONS] FILE...\n  shred file       overwrite file data\n  shred -u file    overwrite and remove")
        return
    if not _require_host(game): return
    host = game.current_host
    remove = "-u" in args
    for a in args:
        if a.startswith("-"): continue
        fp = a if a.startswith("/") else _resolve_path(host.cwd, a)
        if fp not in host.files:
            console.print_error(f"shred: {a}: No such file")
            continue
        console.print(f"shred: {a}: pass 1/3 (random)...")
        console.print(f"shred: {a}: pass 2/3 (random)...")
        console.print(f"shred: {a}: pass 3/3 (zeros)...")
        if remove:
            host.files.pop(fp, None)
            host.user_files[fp] = "__DELETED__"
            console.print(f"shred: {a}: removed")


# ── w / who / users / last ──

@register("w", "cmd.w.help", required_tool="w")
def handle_w(game, args):
    if not _require_host(game): return
    host = game.current_host
    user = host.get_current_user()
    up_d = random.randint(1, 365)
    console.print(f" 14:32:01 up {up_d} days,  1 user,  load average: 0.{random.randint(0,99):02d}, 0.{random.randint(0,99):02d}, 0.{random.randint(0,99):02d}")
    console.print(f"{'USER':10s} {'TTY':8s} {'FROM':16s} {'LOGIN@':8s} {'IDLE':6s} {'WHAT'}")
    console.print(f"{user:10s} {'pts/0':8s} {host.ip:16s} {'14:30':8s} {'0.00s':6s} -bash")

@register("who", "cmd.who.help", required_tool="who")
def handle_who(game, args):
    if not _require_host(game): return
    user = game.current_host.get_current_user()
    console.print(f"{user:10s} pts/0        2024-11-15 14:30 ({game.current_host.ip})")

@register("users", "cmd.users.help", required_tool="users")
def handle_users(game, args):
    if not _require_host(game): return
    console.print(game.current_host.get_current_user())

@register("last", "cmd.last.help", required_tool="last")
def handle_last(game, args):
    if not _require_host(game): return
    host = game.current_host
    user = host.get_current_user()
    n = 10
    if args and args[0].startswith("-") and args[0][1:].isdigit():
        n = int(args[0][1:])
    for i in range(min(n, 5)):
        day = 15 - i
        console.print(f"{user:10s} pts/0        {host.ip:16s} Fri Nov {day} 14:30   still logged in")
    console.print(f"{'reboot':10s} system boot  5.4.0-42-generic Fri Nov 10 10:00   still running")
    console.print(f"\nwtmp begins Fri Nov 10 10:00:01 2024")


# ── yes ──

@register("yes", "cmd.yes.help", required_tool="yes")
def handle_yes(game, args):
    if _wants_help(args):
        console.print("Usage: yes [STRING]\n  yes       repeatedly output 'y'\n  yes text  repeatedly output 'text'")
        return
    text = " ".join(args) if args else "y"
    for _ in range(50):  # limited for game
        console.print(text)


# ── mktemp ──

@register("mktemp", "cmd.mktemp.help", required_tool="mktemp")
def handle_mktemp(game, args):
    if _wants_help(args):
        console.print("Usage: mktemp [TEMPLATE]\n  mktemp            create temp file\n  mktemp -d         create temp directory")
        return
    if not _require_host(game): return
    host = game.current_host
    suffix = f"{random.randint(100000,999999)}"
    is_dir = "-d" in args
    if is_dir:
        path = f"/tmp/tmp.{suffix}"
        from commands.file_edit_cmds import _track_file
        _track_file(host, f"{path}/.keep", "")
    else:
        path = f"/tmp/tmp.{suffix}"
        from commands.file_edit_cmds import _track_file
        _track_file(host, path, "")
    console.print(path)


# ── tac (reverse cat) ──

@register("tac", "cmd.tac.help", required_tool="tac")
def handle_tac(game, args):
    if _wants_help(args):
        console.print("Usage: tac [FILE]\n  tac file    print file in reverse line order\n  cmd | tac   reverse piped input")
        return
    if not _require_host(game): return
    content = _get_input(game, args, "tac")
    if content is None: return
    for line in reversed(content.split("\n")):
        console.print(line)


# ── comm (compare sorted files) ──

@register("comm", "cmd.comm.help", required_tool="comm")
def handle_comm(game, args):
    if _wants_help(args):
        console.print("Usage: comm [OPTIONS] FILE1 FILE2\n  comm file1 file2      3-column output\n  comm -12 file1 file2  show only common lines")
        return
    if not _require_host(game): return
    host = game.current_host
    non_flag = [a for a in args if not a.startswith("-")]
    if len(non_flag) < 2:
        console.print_error("comm: missing operand")
        return
    f1 = non_flag[0] if non_flag[0].startswith("/") else _resolve_path(host.cwd, non_flag[0])
    f2 = non_flag[1] if non_flag[1].startswith("/") else _resolve_path(host.cwd, non_flag[1])
    for fp, n in [(f1, non_flag[0]), (f2, non_flag[1])]:
        if fp not in host.files:
            console.print_error(f"comm: {n}: No such file")
            return
    lines1 = set(host.files[f1].split("\n"))
    lines2 = set(host.files[f2].split("\n"))
    flags = "".join(a[1:] for a in args if a.startswith("-"))
    only_common = "1" in flags and "2" in flags
    for line in sorted(lines1 | lines2):
        in1 = line in lines1
        in2 = line in lines2
        if in1 and in2:
            if only_common or "3" not in flags:
                console.print(f"\t\t{line}")
        elif in1 and "1" not in flags:
            console.print(line)
        elif in2 and "2" not in flags:
            console.print(f"\t{line}")


# ── expand / unexpand ──

@register("expand", "cmd.expand.help", required_tool="expand")
def handle_expand(game, args):
    if _wants_help(args):
        console.print("Usage: expand [OPTIONS] [FILE]\n  expand file      convert tabs to spaces\n  expand -t 4 file  tab width 4")
        return
    if not _require_host(game): return
    tab_w = 8
    if "-t" in args:
        idx = args.index("-t")
        if idx + 1 < len(args):
            try: tab_w = int(args[idx + 1])
            except: pass
    content = _get_input(game, args, "expand")
    if content is None: return
    console.print(content.replace("\t", " " * tab_w))

@register("unexpand", "cmd.unexpand.help", required_tool="unexpand")
def handle_unexpand(game, args):
    if _wants_help(args):
        console.print("Usage: unexpand [OPTIONS] [FILE]\n  unexpand file    convert spaces to tabs")
        return
    if not _require_host(game): return
    content = _get_input(game, args, "unexpand")
    if content is None: return
    console.print(content.replace("        ", "\t"))


# ── nohup ──

@register("nohup", "cmd.nohup.help", required_tool="nohup")
def handle_nohup(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: nohup COMMAND [ARGS]\n  nohup command &   run immune to hangups")
        return
    console.print(f"nohup: ignoring input and appending output to 'nohup.out'")
    from commands.registry import dispatch
    dispatch(game, " ".join(args))


# ── reset ──

@register("reset", "cmd.reset.help", required_tool="reset")
def handle_reset(game, args):
    os.system("clear" if os.name != "nt" else "cls")


# ── bzip2/bunzip2 ──

@register("bzip2", "cmd.bzip2.help", required_tool="bzip2")
def handle_bzip2(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: bzip2 [OPTIONS] FILE...\n  bzip2 file       compress (creates file.bz2)\n  bzip2 -d file.bz2  decompress\n  bzip2 -k file    keep original")
        return
    if not _require_host(game): return
    keep = "-k" in args
    decompress = "-d" in args
    files = [a for a in args if not a.startswith("-")]
    from commands.filesystem_cmds import _resolve_path
    host = game.current_host
    for f in files:
        fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
        if decompress:
            src = fp
            dst = fp.replace(".bz2", "") if fp.endswith(".bz2") else fp + ".out"
            if src not in host.files:
                console.print_error(f"bzip2: {src}: No such file or directory")
                continue
            host.files[dst] = host.files[src]
            host.user_files[dst] = host.files[src]
            if not keep:
                del host.files[src]
                host.user_files.pop(src, None)
        else:
            if fp not in host.files:
                console.print_error(f"bzip2: {fp}: No such file or directory")
                continue
            dst = fp + ".bz2"
            host.files[dst] = f"[bzip2 compressed: {len(host.files[fp])} bytes]"
            host.user_files[dst] = host.files[dst]
            host.file_meta[dst] = host.file_meta.get(fp, {"perms": "-rw-r--r--", "owner": "root", "group": "root", "mtime": "May 22 15:00"})
            if not keep:
                del host.files[fp]
                host.user_files.pop(fp, None)

@register("bunzip2", "cmd.bzip2.help", required_tool="bzip2")
def handle_bunzip2(game, args):
    return handle_bzip2(game, ["-d"] + list(args))


# ── xz/unxz ──

@register("xz", "cmd.xz.help", required_tool="xz")
def handle_xz(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: xz [OPTIONS] FILE...\n  xz file         compress (creates file.xz)\n  xz -d file.xz   decompress\n  xz -k file      keep original")
        return
    if not _require_host(game): return
    keep = "-k" in args
    decompress = "-d" in args
    files = [a for a in args if not a.startswith("-")]
    from commands.filesystem_cmds import _resolve_path
    host = game.current_host
    for f in files:
        fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
        if decompress:
            src = fp
            dst = fp.replace(".xz", "") if fp.endswith(".xz") else fp + ".out"
            if src not in host.files:
                console.print_error(f"xz: {src}: No such file or directory")
                continue
            host.files[dst] = host.files[src]
            host.user_files[dst] = host.files[src]
            if not keep:
                del host.files[src]
                host.user_files.pop(src, None)
        else:
            if fp not in host.files:
                console.print_error(f"xz: {fp}: No such file or directory")
                continue
            dst = fp + ".xz"
            host.files[dst] = f"[xz compressed: {len(host.files[fp])} bytes]"
            host.user_files[dst] = host.files[dst]
            host.file_meta[dst] = host.file_meta.get(fp, {"perms": "-rw-r--r--", "owner": "root", "group": "root", "mtime": "May 22 15:00"})
            if not keep:
                del host.files[fp]
                host.user_files.pop(fp, None)

@register("unxz", "cmd.xz.help", required_tool="xz")
def handle_unxz(game, args):
    return handle_xz(game, ["-d"] + list(args))


# ── usermod ──

@register("usermod", "cmd.usermod.help", required_tool="usermod")
def handle_usermod(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: usermod [OPTIONS] LOGIN\n  usermod -aG group user\n  usermod -s /bin/bash user\n  usermod -L user (lock)\n  usermod -U user (unlock)")
        return
    if not _require_host(game): return
    host = game.current_host
    if host.access_level != "root":
        console.print_error("usermod: Permission denied. Are you root?")
        return 1
    user = args[-1]
    console.print_info(f"User '{user}' modified")
    return 0


# ── userdel ──

@register("userdel", "cmd.userdel.help", required_tool="userdel")
def handle_userdel(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: userdel [OPTIONS] LOGIN\n  userdel user\n  userdel -r user (remove home)")
        return
    if not _require_host(game): return
    host = game.current_host
    if host.access_level != "root":
        console.print_error("userdel: Permission denied. Are you root?")
        return 1
    user = args[-1]
    console.print_info(f"User '{user}' deleted")
    return 0


# ── getent ──

@register("getent", "cmd.getent.help", required_tool="getent")
def handle_getent(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: getent DATABASE [KEY]\n  getent passwd\n  getent passwd root\n  getent hosts localhost\n  getent services ssh")
        return
    if not _require_host(game): return
    host = game.current_host
    db = args[0]
    key = args[1] if len(args) > 1 else None
    if db == "passwd":
        content = host.files.get("/etc/passwd", "")
        if key:
            for line in content.split("\n"):
                if line.startswith(key + ":"):
                    console.print(line)
                    return 0
            return 2
        console.print(content)
    elif db == "group":
        content = host.files.get("/etc/group", "")
        if key:
            for line in content.split("\n"):
                if line.startswith(key + ":"):
                    console.print(line)
                    return 0
            return 2
        console.print(content)
    elif db == "hosts":
        if key:
            if key == "localhost":
                console.print("127.0.0.1       localhost")
            else:
                console.print(f"{host.ip}       {key}")
        else:
            console.print(host.files.get("/etc/hosts", ""))
    elif db == "services":
        services_map = {"ssh": "ssh                 22/tcp", "http": "http                80/tcp", "https": "https               443/tcp",
                        "ftp": "ftp                 21/tcp", "smtp": "smtp                25/tcp", "dns": "domain              53/tcp"}
        if key and key in services_map:
            console.print(services_map[key])
        elif not key:
            for v in services_map.values():
                console.print(v)
        else:
            return 2
    else:
        console.print_error(f"getent: unknown database: {db}")
        return 1
    return 0


# ── jobs/bg/fg ──

@register("jobs", "cmd.jobs.help", required_tool="jobs")
def handle_jobs(game, args):
    if _wants_help(args):
        console.print("Usage: jobs [-l]\n  List active jobs.")
        return
    # No real background jobs in simulation
    return 0

@register("bg", "cmd.bg.help", required_tool="bg")
def handle_bg(game, args):
    if _wants_help(args):
        console.print("Usage: bg [JOB_SPEC]\n  Resume JOB_SPEC in the background.")
        return
    console.print_error("bg: no current job")
    return 1

@register("fg", "cmd.fg.help", required_tool="fg")
def handle_fg(game, args):
    if _wants_help(args):
        console.print("Usage: fg [JOB_SPEC]\n  Resume JOB_SPEC in the foreground.")
        return
    console.print_error("fg: no current job")
    return 1


# ── trap ──

@register("trap", "cmd.trap.help", required_tool="trap")
def handle_trap(game, args):
    if _wants_help(args):
        console.print("Usage: trap [-lp] [COMMAND] [SIGNAL]...\n  trap 'echo exit' EXIT\n  trap '' SIGINT\n  trap -l")
        return
    if not args or "-l" in args:
        signals = ["SIGHUP", "SIGINT", "SIGQUIT", "SIGILL", "SIGTRAP", "SIGABRT",
                    "SIGBUS", "SIGFPE", "SIGKILL", "SIGUSR1", "SIGSEGV", "SIGUSR2",
                    "SIGPIPE", "SIGALRM", "SIGTERM", "SIGSTKFLT", "SIGCHLD", "SIGCONT",
                    "SIGSTOP", "SIGTSTP", "SIGTTIN", "SIGTTOU", "SIGURG"]
        for i, sig in enumerate(signals, 1):
            console.print(f"{i:2d}) {sig}", end="  ")
            if i % 5 == 0:
                console.print("")
        if len(signals) % 5 != 0:
            console.print("")
    elif "-p" in args:
        pass  # no traps set
    # Otherwise just accept and ignore (simulation)
    return 0


# ── wait ──

@register("wait", "cmd.wait.help", required_tool="wait")
def handle_wait(game, args):
    if _wants_help(args):
        console.print("Usage: wait [PID...]\n  Wait for background processes to finish.")
        return
    # No real background processes
    return 0


# ── locate ──

@register("locate", "cmd.locate.help", required_tool="locate")
def handle_locate(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: locate [OPTIONS] PATTERN\n  locate passwd\n  locate -i README")
        return
    if not _require_host(game): return
    host = game.current_host
    case_i = "-i" in args
    pattern = [a for a in args if not a.startswith("-")][-1]
    for fp in sorted(host.files.keys()):
        name = fp if case_i else fp
        pat = pattern.lower() if case_i else pattern
        if pat in (name.lower() if case_i else name):
            console.print(fp)
    return 0


# ── whereis ──

@register("whereis", "cmd.whereis.help", required_tool="whereis")
def handle_whereis(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: whereis COMMAND\n  whereis ls\n  whereis python3")
        return
    cmd = args[-1]
    paths = [f"/usr/bin/{cmd}", f"/usr/sbin/{cmd}", f"/bin/{cmd}", f"/sbin/{cmd}"]
    found = []
    if _require_host(game):
        for p in paths:
            if p in game.current_host.files:
                found.append(p)
    if not found:
        found = [f"/usr/bin/{cmd}"]
    console.print(f"{cmd}: {' '.join(found)}")
    return 0


# ── cal ──

@register("cal", "cmd.cal.help", required_tool="cal")
def handle_cal(game, args):
    if _wants_help(args):
        console.print("Usage: cal [MONTH] [YEAR]\n  cal          show current month\n  cal 12 2024  show December 2024")
        return
    import calendar
    import datetime
    now = datetime.datetime.now()
    month, year = now.month, now.year
    if len(args) >= 2:
        try: month, year = int(args[0]), int(args[1])
        except: pass
    elif len(args) == 1:
        try: year = int(args[0])
        except: pass
        else: month = None
    if month:
        console.print(calendar.month(year, month).rstrip())
    else:
        console.print(calendar.calendar(year).rstrip())
    return 0


# ── bc ──

@register("bc", "cmd.bc.help", required_tool="bc")
def handle_bc(game, args):
    if _wants_help(args):
        console.print("Usage: bc\n  echo '2+3' | bc\n  echo 'scale=2; 10/3' | bc")
        return
    content = game.stdin if hasattr(game, "stdin") and game.stdin else None
    if not content:
        console.print("bc 1.07.1")
        console.print("(interactive mode not supported, use: echo 'expr' | bc)")
        return
    import re as _re
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"): continue
        line = _re.sub(r"scale\s*=\s*\d+\s*;?\s*", "", line)
        try:
            safe = line.replace("^", "**")
            result = eval(safe, {"__builtins__": {}}, {})
            console.print(str(result))
        except Exception:
            console.print_error(f"(standard_in) 1: parse error: {line}")
    return 0


# ── watch ──

@register("watch", "cmd.watch.help", required_tool="watch")
def handle_watch(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: watch [OPTIONS] COMMAND\n  watch -n 2 ls -l\n  watch date")
        return
    cmd_args = [a for a in args if not a.startswith("-n")]
    # Skip -n value
    filtered = []
    skip = False
    for a in args:
        if skip: skip = False; continue
        if a == "-n": skip = True; continue
        if a.startswith("-n"): continue
        filtered.append(a)
    console.print(f"Every 2.0s: {' '.join(filtered)}\n")
    from commands.registry import dispatch
    dispatch(game, " ".join(filtered))
    return 0


# ── lscpu ──

@register("lscpu", "cmd.lscpu.help", required_tool="lscpu")
def handle_lscpu(game, args):
    if _wants_help(args):
        console.print("Usage: lscpu\n  Display CPU architecture information.")
        return
    lines = [
        "Architecture:          x86_64",
        "CPU op-mode(s):        32-bit, 64-bit",
        "Byte Order:            Little Endian",
        "CPU(s):                4",
        "On-line CPU(s) list:   0-3",
        "Thread(s) per core:    2",
        "Core(s) per socket:    2",
        "Socket(s):             1",
        "Vendor ID:             GenuineIntel",
        "CPU family:            6",
        "Model:                 142",
        f"Model name:            Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz",
        "CPU MHz:               2400.000",
        "L1d cache:             32K",
        "L1i cache:             32K",
        "L2 cache:              256K",
        "L3 cache:              35840K",
    ]
    for line in lines:
        console.print(line)
    return 0


# ── lsusb ──

@register("lsusb", "cmd.lsusb.help", required_tool="lsusb")
def handle_lsusb(game, args):
    if _wants_help(args):
        console.print("Usage: lsusb [-v]\n  List USB devices.")
        return
    devices = [
        "Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub",
        "Bus 001 Device 002: ID 8087:0024 Intel Corp. Integrated Rate Matching Hub",
        "Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub",
        "Bus 001 Device 003: ID 0627:0001 Adomax Technology Co., Ltd QEMU Tablet",
    ]
    for d in devices:
        console.print(d)
    return 0


# ── lspci ──

@register("lspci", "cmd.lspci.help", required_tool="lspci")
def handle_lspci(game, args):
    if _wants_help(args):
        console.print("Usage: lspci [-v]\n  List PCI devices.")
        return
    devices = [
        "00:00.0 Host bridge: Intel Corporation 440FX - 82441FX PMC [Natoma]",
        "00:01.0 ISA bridge: Intel Corporation 82371SB PIIX3 ISA [Natoma/Triton II]",
        "00:01.1 IDE interface: Intel Corporation 82371SB PIIX3 IDE [Natoma/Triton II]",
        "00:02.0 VGA compatible controller: Red Hat, Inc. QXL paravirtual graphic card",
        "00:03.0 Ethernet controller: Red Hat, Inc. Virtio network device",
        "00:1f.2 SATA controller: Intel Corporation 82801HM/HEM SATA Controller [AHCI mode]",
    ]
    for d in devices:
        console.print(d)
    return 0


# ── vmstat ──

@register("vmstat", "cmd.vmstat.help", required_tool="vmstat")
def handle_vmstat(game, args):
    if _wants_help(args):
        console.print("Usage: vmstat [delay [count]]\n  vmstat        show VM statistics\n  vmstat 1 5   every 1s, 5 times")
        return
    console.print("procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----")
    console.print(" r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st")
    count = 1
    if args:
        try: count = int(args[-1]) if len(args) > 1 else 1
        except: pass
    for _ in range(min(count, 5)):
        r, b = random.randint(0, 3), random.randint(0, 1)
        free = random.randint(100000, 800000)
        buff = random.randint(30000, 120000)
        cache = random.randint(500000, 2000000)
        us = random.randint(1, 30)
        sy = random.randint(0, 10)
        idle = 100 - us - sy
        console.print(f" {r}  {b}      0 {free:>7d} {buff:>6d} {cache:>7d}    0    0   {random.randint(0,50):>3d}   {random.randint(0,80):>3d} {random.randint(50,300):>4d} {random.randint(80,500):>4d} {us:>2d} {sy:>2d} {idle:>2d}  0  0")
    return 0


# ── openssl ──

@register("openssl", "cmd.openssl.help", required_tool="openssl")
def handle_openssl(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: openssl COMMAND [OPTIONS]\n  openssl rand -hex 16\n  openssl md5 file\n  openssl enc -base64\n  openssl version\n  openssl genrsa 2048\n  openssl s_client -connect H:P")
        return
    subcmd = args[0]
    if subcmd == "version":
        console.print("OpenSSL 3.0.2 15 Mar 2022 (Library: OpenSSL 3.0.2 15 Mar 2022)")
    elif subcmd == "rand":
        n = 16
        fmt = "-hex"
        if "-hex" in args:
            fmt = "hex"
            idx = args.index("-hex")
            if idx + 1 < len(args):
                try: n = int(args[idx + 1])
                except: pass
        elif "-base64" in args:
            fmt = "b64"
            idx = args.index("-base64")
            if idx + 1 < len(args):
                try: n = int(args[idx + 1])
                except: pass
        data = bytes(random.randint(0, 255) for _ in range(n))
        if fmt == "hex":
            console.print(data.hex())
        else:
            import base64
            console.print(base64.b64encode(data).decode())
    elif subcmd in ("md5", "sha1", "sha256"):
        import hashlib
        content = ""
        if hasattr(game, "stdin") and game.stdin:
            content = game.stdin
        elif len(args) > 1:
            if _require_host(game):
                fp = args[1] if args[1].startswith("/") else _resolve_path(game.current_host.cwd, args[1])
                content = game.current_host.files.get(fp, "")
        h = hashlib.new(subcmd, content.encode()).hexdigest()
        console.print(f"{'(stdin)' if not (len(args)>1) else args[1]}= {h}")
    elif subcmd == "enc":
        import base64
        content = game.stdin if hasattr(game, "stdin") and game.stdin else ""
        if "-base64" in args and "-d" in args:
            try: console.print(base64.b64decode(content.strip()).decode())
            except: console.print_error("bad base64 input")
        elif "-base64" in args:
            console.print(base64.b64encode(content.encode()).decode())
        else:
            console.print_error("openssl enc: unknown cipher")
    elif subcmd == "genrsa":
        bits = 2048
        if len(args) > 1:
            try: bits = int(args[1])
            except: pass
        console.print(f"Generating RSA private key, {bits} bit long modulus")
        console.print("..........+++")
        console.print("...+++")
        console.print("e is 65537 (0x010001)")
    elif subcmd == "s_client":
        target = "localhost:443"
        if "-connect" in args:
            idx = args.index("-connect")
            if idx + 1 < len(args):
                target = args[idx + 1]
        host_part = target.partition(":")[0]
        serial = "".join(f"{random.randint(0,255):02X}" for _ in range(16))
        console.print("CONNECTED(00000003)")
        console.print("---")
        console.print("Certificate chain")
        console.print(f" 0 s:CN = {host_part}")
        console.print("   i:C = US, O = Let's Encrypt, CN = R3")
        console.print("---")
        console.print("Server certificate")
        console.print("-----BEGIN CERTIFICATE-----")
        for _ in range(4):
            console.print("".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/") for _ in range(64)))
        console.print("-----END CERTIFICATE-----")
        console.print(f"subject=CN = {host_part}")
        console.print("issuer=C = US, O = Let's Encrypt, CN = R3")
        console.print("---")
        console.print("No client certificate CA names sent")
        console.print(f"SSL handshake has read 3456 bytes and written 392 bytes")
        console.print("    Protocol  : TLSv1.3")
        console.print("    Cipher    : TLS_AES_256_GCM_SHA384")
        console.print(f"    Session-ID: {serial}")
        console.print("---")
    else:
        console.print_error(f"openssl: '{subcmd}' is an invalid command.")
    return 0


# ── git ──

@register("git", "cmd.git.help", required_tool="git")
def handle_git(game, args):
    if _wants_help(args) or not args:
        console.print("usage: git <command> [<args>]\n  git status    Show working tree status\n  git log       Show commit log\n  git branch    List branches\n  git diff      Show changes")
        return
    subcmd = args[0]
    if subcmd == "status":
        console.print("On branch main\nnothing to commit, working tree clean")
    elif subcmd == "log":
        for i in range(3):
            h = '%032x' % random.randint(0, 16**32)
            console.print(f"[yellow]commit {h[:40]}[/yellow]")
            console.print(f"Author: admin <admin@localhost>")
            console.print(f"Date:   Mon Nov {11+i} 10:{10+i}:00 2024\n")
            console.print(f"    {'Initial commit' if i==2 else 'Update config' if i==1 else 'Fix bug'}\n")
    elif subcmd == "branch":
        console.print("* [green]main[/green]")
    elif subcmd == "diff":
        console.print("")  # no changes
    elif subcmd == "init":
        console.print("Initialized empty Git repository in .git/")
    elif subcmd == "clone":
        if len(args) > 1:
            console.print(f"Cloning into '{args[1].rsplit('/',1)[-1].replace('.git','')}'...")
            console.print("remote: Enumerating objects: 47, done.")
            console.print("Receiving objects: 100% (47/47), done.")
        else:
            console.print_error("usage: git clone <repository>")
    else:
        console.print(f"git: '{subcmd}' is not a git command. See 'git --help'.")
    return 0


# ── python3 ──

@register("python3", "cmd.python3.help", required_tool="python3")
def handle_python3(game, args):
    if not args:
        console.print("Python 3.10.12 (main, Nov 20 2023, 15:14:05) [GCC 11.4.0] on linux")
        console.print("Type \"help\", \"copyright\", \"credits\" or \"license\" for more information.")
        console.print("(interactive mode not supported, use: python3 -c 'code')")
        return
    if args[0] == "--version" or args[0] == "-V":
        console.print("Python 3.10.12")
        return
    if args[0] == "-c" and len(args) > 1:
        code = " ".join(args[1:])
        # Strip surrounding quotes
        if (code.startswith("'") and code.endswith("'")) or (code.startswith('"') and code.endswith('"')):
            code = code[1:-1]
        try:
            exec(code, {"__builtins__": {"print": lambda *a, **kw: console.print(" ".join(str(x) for x in a)),
                                          "range": range, "len": len, "int": int, "str": str, "float": float,
                                          "list": list, "sum": sum, "max": max, "min": min, "sorted": sorted}})
        except Exception as e:
            console.print_error(f"Traceback (most recent call last):\n  File \"<string>\", line 1\n{type(e).__name__}: {e}")
    else:
        console.print_error(f"python3: can't open file '{args[0]}': [Errno 2] No such file or directory")
    return 0


# ── gcc ──

@register("gcc", "cmd.gcc.help", required_tool="gcc")
def handle_gcc(game, args):
    if not args or _wants_help(args):
        console.print("Usage: gcc [OPTIONS] FILE...\n  gcc file.c -o output\n  gcc --version")
        return
    if args[0] == "--version":
        console.print("gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0")
        console.print("Copyright (C) 2021 Free Software Foundation, Inc.")
        return
    src = [a for a in args if not a.startswith("-") and a != "-o" and args[args.index(a)-1:args.index(a)] != ["-o"]]
    if not src:
        console.print_error("gcc: fatal error: no input files\ncompilation terminated.")
        return 1
    outname = "a.out"
    if "-o" in args:
        idx = args.index("-o")
        if idx + 1 < len(args): outname = args[idx + 1]
    console.print(f"[dim]{src[0]}: In function 'main':[/dim]")
    console.print(f"[dim]compilation successful → {outname}[/dim]")
    return 0


# ── make ──

@register("make", "cmd.make.help", required_tool="make")
def handle_make(game, args):
    if _wants_help(args):
        console.print("Usage: make [TARGET]\n  make        build default target\n  make clean  clean build artifacts\n  make install")
        return
    if not args or args[0] == "all":
        console.print("make: Nothing to be done for 'all'.")
    elif args[0] == "clean":
        console.print("rm -f *.o a.out")
    elif args[0] == "install":
        console.print("install -m 755 program /usr/local/bin/")
    else:
        console.print(f"make: *** No rule to make target '{args[0]}'.  Stop.")
        return 2
    return 0


# ── telnet, arp, tcpdump ── moved to commands/net_tools.py


# ── nice ──

@register("nice", "cmd.nice.help", required_tool="nice")
def handle_nice(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: nice [OPTION] COMMAND\n  nice -n 10 command\n  nice command")
        return
    priority = 10
    cmd_parts = []
    skip = False
    for i, a in enumerate(args):
        if skip: skip = False; continue
        if a == "-n":
            skip = True
            if i + 1 < len(args):
                try: priority = int(args[i + 1])
                except: pass
            continue
        if a.startswith("-n"):
            try: priority = int(a[2:])
            except: pass
            continue
        cmd_parts.append(a)
    if cmd_parts:
        from commands.registry import dispatch
        dispatch(game, " ".join(cmd_parts))
    return 0


# ── renice ──

@register("renice", "cmd.renice.help", required_tool="renice")
def handle_renice(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: renice [-n] PRIORITY [-p PID]\n  renice -n 5 -p 1234")
        return
    pid = args[-1] if args[-1].isdigit() else "1"
    prio = "0"
    if "-n" in args:
        idx = args.index("-n")
        if idx + 1 < len(args): prio = args[idx + 1]
    console.print(f"{pid} (process ID) old priority 0, new priority {prio}")
    return 0


# ── stty ──

@register("stty", "cmd.stty.help", required_tool="stty")
def handle_stty(game, args):
    if _wants_help(args):
        console.print("Usage: stty [OPTIONS]\n  stty -a     show all settings\n  stty size   show rows and columns")
        return
    if args and args[0] == "size":
        console.print("24 80")
        return 0
    if not args or "-a" in args:
        console.print("speed 38400 baud; rows 24; columns 80; line = 0;")
        console.print("intr = ^C; quit = ^\\; erase = ^?; kill = ^U; eof = ^D; eol = <undef>;")
        console.print("start = ^Q; stop = ^S; susp = ^Z; rprnt = ^R; werase = ^W; lnext = ^V;")
        console.print("-parenb -parodd -cmspar cs8 -hupcl -cstopb cread -clocal -crtscts")
        console.print("-ignbrk -brkint -ignpar -parmrk -inpck -istrip -inlcr -igncr icrnl ixon -ixoff")
        console.print("opost -olcuc -ocrnl onlcr -onocr -onlret -ofill -ofdel nl0 cr0 tab0 bs0 vt0 ff0")
        console.print("isig icanon iexten echo echoe echok -echonl -noflsh -xcase -tostop -echoprt")
    return 0


# ── screen ──

@register("screen", "cmd.screen.help", required_tool="screen")
def handle_screen(game, args):
    if _wants_help(args):
        console.print("Usage: screen [OPTIONS]\n  screen          start new session\n  screen -ls      list sessions\n  screen -r       reattach")
        return
    if args and args[0] == "--version":
        console.print("Screen version 4.09.00 (GNU) 30-Jan-22")
        return
    if args and args[0] == "-ls":
        console.print("No Sockets found in /run/screen/S-user.")
        return
    if args and args[0] == "-r":
        console.print("There is no screen to be resumed.")
        return
    console.print("[screen is terminating]")
    return 0


# ── tmux ──

@register("tmux", "cmd.tmux.help", required_tool="tmux")
def handle_tmux(game, args):
    if _wants_help(args):
        console.print("Usage: tmux [OPTIONS]\n  tmux             start new session\n  tmux ls          list sessions\n  tmux new -s name start named session")
        return
    if args and args[0] in ("-V", "--version"):
        console.print("tmux 3.3a")
        return
    if args and args[0] == "ls":
        console.print("no server running on /tmp/tmux-1000/default")
        return
    if args and args[0] in ("new", "new-session"):
        console.print("[detached (from session 0)]")
        return
    if not args:
        console.print("[exited]")
    return 0


# ── logger ──

@register("logger", "cmd.logger.help", required_tool="logger")
def handle_logger(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: logger [OPTIONS] MESSAGE\n  logger 'System started'\n  logger -t mytag 'message'\n  logger -p local0.info 'msg'")
        return
    if not _require_host(game): return
    tag = "user"
    if "-t" in args:
        idx = args.index("-t")
        if idx + 1 < len(args): tag = args[idx + 1]
    msg_parts = [a for a in args if not a.startswith("-") and a != tag]
    msg = " ".join(msg_parts)
    host = game.current_host
    syslog = host.files.get("/var/log/syslog", "")
    import datetime
    ts = datetime.datetime.now().strftime("%b %d %H:%M:%S")
    entry = f"{ts} {host.hostname} {tag}: {msg}"
    host.files["/var/log/syslog"] = (syslog + "\n" + entry).lstrip("\n")
    host.user_files["/var/log/syslog"] = host.files["/var/log/syslog"]
    return 0


# ── wall ──

@register("wall", "cmd.wall.help", required_tool="wall")
def handle_wall(game, args):
    if _wants_help(args):
        console.print("Usage: wall [MESSAGE]\n  wall 'System going down'\n  echo msg | wall")
        return
    if not _require_host(game): return
    msg = ""
    if args:
        msg = " ".join(args)
    elif hasattr(game, "stdin") and game.stdin:
        msg = game.stdin.strip()
    user = game.current_host.get_current_user()
    console.print(f"\nBroadcast message from {user}@{game.current_host.hostname} (pts/0):")
    console.print(f"\n        {msg}\n")
    return 0


# ── fold ──

@register("fold", "cmd.fold.help", required_tool="fold")
def handle_fold(game, args):
    if _wants_help(args):
        console.print("Usage: fold [OPTIONS] [FILE]\n  fold -w 40 file   wrap at 40 columns\n  echo text | fold -w 20")
        return
    width = 80
    if "-w" in args:
        idx = args.index("-w")
        if idx + 1 < len(args):
            try: width = int(args[idx + 1])
            except: pass
    for a in args:
        if a.startswith("-w") and len(a) > 2:
            try: width = int(a[2:])
            except: pass
    content = _get_input(game, args, "fold")
    if content is None: return
    for line in content.split("\n"):
        while len(line) > width:
            console.print(line[:width])
            line = line[width:]
        console.print(line)
    return 0


# ── fmt ──

@register("fmt", "cmd.fmt.help", required_tool="fmt")
def handle_fmt(game, args):
    if _wants_help(args):
        console.print("Usage: fmt [OPTIONS] [FILE]\n  fmt -w 60 file   reformat to 60 columns\n  echo text | fmt -w 40")
        return
    width = 75
    if "-w" in args:
        idx = args.index("-w")
        if idx + 1 < len(args):
            try: width = int(args[idx + 1])
            except: pass
    content = _get_input(game, args, "fmt")
    if content is None: return
    for paragraph in content.split("\n\n"):
        words = paragraph.split()
        if not words:
            console.print("")
            continue
        lines, cur = [], words[0]
        for w in words[1:]:
            if len(cur) + 1 + len(w) <= width:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        for l in lines:
            console.print(l)
    return 0


# ── mkfifo ──

@register("mkfifo", "cmd.mkfifo.help", required_tool="mkfifo")
def handle_mkfifo(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: mkfifo NAME\n  Create a named pipe (FIFO).")
        return
    if not _require_host(game): return
    host = game.current_host
    for name in args:
        if name.startswith("-"): continue
        fp = name if name.startswith("/") else _resolve_path(host.cwd, name)
        host.files[fp] = "[fifo]"
        host.file_meta[fp] = {"perms": "prw-r--r--", "owner": host.get_current_user(),
                              "group": host.get_current_user(), "mtime": "Jun  9 12:00"}
    return 0


# ── truncate ──

@register("truncate", "cmd.truncate.help", required_tool="truncate")
def handle_truncate(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: truncate -s SIZE FILE\n  truncate -s 0 file   empty a file\n  truncate -s 1M file  set to 1MB")
        return
    if not _require_host(game): return
    host = game.current_host
    size = 0
    files = []
    i = 0
    while i < len(args):
        if args[i] == "-s" and i + 1 < len(args):
            s = args[i + 1]
            try:
                if s.endswith("K"): size = int(s[:-1]) * 1024
                elif s.endswith("M"): size = int(s[:-1]) * 1048576
                elif s.endswith("G"): size = int(s[:-1]) * 1073741824
                else: size = int(s)
            except ValueError: pass
            i += 2
        elif not args[i].startswith("-"):
            files.append(args[i])
            i += 1
        else:
            i += 1
    for f in files:
        fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
        host.files[fp] = "\0" * min(size, 1024)  # simulate, cap at 1K
        host.user_files[fp] = host.files[fp]
    return 0


# ── install ──

@register("install", "cmd.install.help", required_tool="install")
def handle_install(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: install [OPTIONS] SOURCE DEST\n  install -m 755 file /usr/local/bin/\n  install -d directory")
        return
    if not _require_host(game): return
    host = game.current_host
    if "-d" in args:
        dirs = [a for a in args if not a.startswith("-")]
        for d in dirs:
            dp = d if d.startswith("/") else _resolve_path(host.cwd, d)
            host.files[dp + "/."] = ""
        return 0
    non_flag = [a for a in args if not a.startswith("-")]
    if len(non_flag) >= 2:
        src_path = non_flag[0] if non_flag[0].startswith("/") else _resolve_path(host.cwd, non_flag[0])
        dst = non_flag[-1] if non_flag[-1].startswith("/") else _resolve_path(host.cwd, non_flag[-1])
        if src_path in host.files:
            host.files[dst] = host.files[src_path]
            host.user_files[dst] = host.files[dst]
    return 0


# ── split ──

@register("split", "cmd.split.help", required_tool="split")
def handle_split(game, args):
    if _wants_help(args):
        console.print("Usage: split [OPTIONS] [FILE [PREFIX]]\n  split -l 100 file   split every 100 lines\n  split -b 1M file    split every 1MB")
        return
    if not _require_host(game): return
    host = game.current_host
    lines_per = 1000
    if "-l" in args:
        idx = args.index("-l")
        if idx + 1 < len(args):
            try: lines_per = int(args[idx + 1])
            except: pass
    content = _get_input(game, [a for a in args if a not in ("-l", str(lines_per))], "split")
    if not content: return
    prefix = "x"
    non_flag = [a for a in args if not a.startswith("-")]
    if len(non_flag) >= 2: prefix = non_flag[1]
    all_lines = content.split("\n")
    part = 0
    for i in range(0, len(all_lines), lines_per):
        chunk = "\n".join(all_lines[i:i + lines_per])
        suffix = chr(ord("a") + part // 26) + chr(ord("a") + part % 26)
        fp = _resolve_path(host.cwd, f"{prefix}{suffix}")
        host.files[fp] = chunk
        host.user_files[fp] = chunk
        part += 1
    console.print_info(f"Split into {part} file(s)")
    return 0


# ── tput ──

@register("tput", "cmd.tput.help", required_tool="tput")
def handle_tput(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: tput CAPABILITY\n  tput cols     columns\n  tput lines    lines\n  tput reset    reset terminal\n  tput clear    clear screen")
        return
    cap = args[0]
    if cap == "cols": console.print("80")
    elif cap == "lines": console.print("24")
    elif cap in ("reset", "clear"): os.system("clear" if os.name != "nt" else "cls")
    elif cap == "bold": console.print("\033[1m", end="")
    elif cap == "sgr0": console.print("\033[0m", end="")
    elif cap == "setaf" and len(args) > 1:
        console.print(f"\033[3{args[1]}m", end="")
    elif cap == "cup" and len(args) > 2:
        console.print(f"\033[{args[1]};{args[2]}H", end="")
    elif cap == "smcup": pass
    elif cap == "rmcup": pass
    else: console.print("")
    return 0


# ── dc ──

@register("dc", "cmd.dc.help", required_tool="dc")
def handle_dc(game, args):
    if _wants_help(args):
        console.print("Usage: dc\n  echo '2 3 + p' | dc    → 5\n  Reverse Polish notation calculator")
        return
    content = game.stdin if hasattr(game, "stdin") and game.stdin else None
    if not content:
        console.print("dc: (interactive mode not supported, use: echo 'expr' | dc)")
        return
    stack = []
    for token in content.strip().split():
        if token == "p":
            if stack: console.print(str(stack[-1]))
        elif token == "f":
            for v in reversed(stack): console.print(str(v))
        elif token in ("+", "-", "*", "/", "%"):
            if len(stack) >= 2:
                b, a = stack.pop(), stack.pop()
                if token == "+": stack.append(a + b)
                elif token == "-": stack.append(a - b)
                elif token == "*": stack.append(a * b)
                elif token == "/": stack.append(a // b if b else 0)
                elif token == "%": stack.append(a % b if b else 0)
        else:
            try: stack.append(int(token))
            except:
                try: stack.append(float(token))
                except: pass
    return 0


# ── join ──

@register("join", "cmd.join.help", required_tool="join")
def handle_join(game, args):
    if _wants_help(args):
        console.print("Usage: join [OPTIONS] FILE1 FILE2\n  join file1 file2   join on first field\n  join -t: -1 2 -2 1 file1 file2")
        return
    if not _require_host(game): return
    console.print_error("join: requires two files (simplified)")
    return 1


# ── htop ──

@register("htop", "cmd.htop.help", required_tool="htop")
def handle_htop(game, args):
    """htop is an alias for top in our simulation."""
    from commands.registry import dispatch
    dispatch(game, ["top"] + list(args))
    return 0


# ── chroot ──

@register("chroot", "cmd.chroot.help", required_tool="chroot")
def handle_chroot(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: chroot NEWROOT [COMMAND]\n  chroot /mnt /bin/bash")
        return
    if not _require_host(game): return
    if game.current_host.access_level != "root":
        console.print_error("chroot: must be run as root")
        return 1
    console.print_info(f"Changed root to {args[0]}")
    return 0


# ── less / more ──

@register("less", "cmd.less.help", required_tool="less")
def handle_less(game, args):
    if _wants_help(args):
        console.print("Usage: less [file]\n  View file contents (pager)")
        return
    from commands.filesystem_cmds import handle_cat
    return handle_cat(game, args)

@register("more", "cmd.more.help", required_tool="more")
def handle_more(game, args):
    if _wants_help(args):
        console.print("Usage: more [file]\n  View file contents (pager)")
        return
    from commands.filesystem_cmds import handle_cat
    return handle_cat(game, args)


# ── tree ──

@register("tree", "cmd.tree.help", required_tool="tree")
def handle_tree(game, args):
    if _wants_help(args):
        console.print("Usage: tree [directory]\n  List contents of directories in a tree-like format")
        return
    if not _require_host(game): return
    host = game.current_host
    path = _resolve_path(host.cwd, args[0]) if args else host.cwd
    path = path.rstrip("/") or "/"

    # Collect direct children grouped by directory
    all_paths = sorted(host.files.keys())
    prefix = path if path == "/" else path + "/"

    def _tree(base, indent=""):
        children = []
        dirs_seen = set()
        for fp in all_paths:
            if not fp.startswith(prefix if base == path else base + "/"):
                continue
            rel = fp[len(base):].lstrip("/")
            top = rel.split("/")[0]
            if "/" in rel:
                if top not in dirs_seen:
                    dirs_seen.add(top)
                    children.append((top, True))
            else:
                children.append((top, False))
        children.sort()
        for i, (name, is_dir) in enumerate(children):
            connector = "└── " if i == len(children) - 1 else "├── "
            ext = "    " if i == len(children) - 1 else "│   "
            if is_dir:
                console.print(f"{indent}{connector}[bold blue]{name}[/bold blue]")
                _tree(base.rstrip("/") + "/" + name, indent + ext)
            else:
                console.print(f"{indent}{connector}{name}")

    console.print(f"[bold blue]{path}[/bold blue]")
    _tree(path)
    return 0


# ── time ──

@register("time", "cmd.time.help", required_tool="time")
def handle_time(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: time COMMAND\n  Run command and report time taken")
        return
    from commands.registry import dispatch
    rc = dispatch(game, args)
    ms = random.randint(1, 15)
    console.print(f"\nreal\t0m0.{ms:03d}s\nuser\t0m0.{max(1, ms - 1):03d}s\nsys\t0m0.001s")
    return rc


# ── dd ──

@register("dd", "cmd.dd.help", required_tool="dd")
def handle_dd(game, args):
    if _wants_help(args):
        console.print("Usage: dd [if=FILE] [of=FILE] [bs=SIZE] [count=N]\n  Convert and copy a file")
        return
    if not _require_host(game): return
    host = game.current_host
    params = {}
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            params[k] = v
    of = params.get("of")
    count = int(params.get("count", "1"))
    bs_str = params.get("bs", "512")
    bs = int(bs_str.upper().replace("K", "000").replace("M", "000000").replace("G", "000000000")) if not bs_str.isdigit() else int(bs_str)
    total = bs * count
    if of:
        fpath = _resolve_path(host.cwd, of)
        host.files[fpath] = "\x00" * min(total, 1024)
        host.user_files[fpath] = host.files[fpath]
    console.print(f"{count}+0 records in\n{count}+0 records out\n{total} bytes ({total // 1024} KB) copied, 0.00{random.randint(1, 99)}s")
    return 0


# ── umask ──

@register("umask", "cmd.umask.help", required_tool="umask")
def handle_umask(game, args):
    if _wants_help(args):
        console.print("Usage: umask [MODE]\n  Display or set file mode creation mask")
        return
    if not args:
        val = game.shell_vars.get("UMASK", "0022")
        console.print(val)
    else:
        game.shell_vars["UMASK"] = args[0]
    return 0


# ── ulimit ──

@register("ulimit", "cmd.ulimit.help", required_tool="ulimit")
def handle_ulimit(game, args):
    if _wants_help(args):
        console.print("Usage: ulimit [-a] [-n] [-u] [-s] [-v]\n  Display or modify shell resource limits")
        return
    limits = {
        "core file size": ("blocks", "0"),
        "data seg size": ("kbytes", "unlimited"),
        "scheduling priority": ("", "0"),
        "file size": ("blocks", "unlimited"),
        "pending signals": ("", "63432"),
        "max locked memory": ("kbytes", "65536"),
        "max memory size": ("kbytes", "unlimited"),
        "open files": ("", "1024"),
        "pipe size": ("512 bytes", "8"),
        "POSIX message queues": ("bytes", "819200"),
        "real-time priority": ("", "0"),
        "stack size": ("kbytes", "8192"),
        "cpu time": ("seconds", "unlimited"),
        "max user processes": ("", "63432"),
        "virtual memory": ("kbytes", "unlimited"),
        "file locks": ("", "unlimited"),
    }
    if "-a" in args or not args:
        for name, (unit, val) in limits.items():
            u = f"({unit}) " if unit else ""
            console.print(f"{name:30s} {u}{val}")
    elif "-n" in args:
        console.print("1024")
    elif "-u" in args:
        console.print("63432")
    elif "-s" in args:
        console.print("8192")
    else:
        console.print("1024")
    return 0


# ── sysctl ──

@register("sysctl", "cmd.sysctl.help", required_tool="sysctl")
def handle_sysctl(game, args):
    if _wants_help(args):
        console.print("Usage: sysctl [-a] [variable] [variable=value]\n  Configure kernel parameters at runtime")
        return
    fake_params = {
        "kernel.hostname": os.uname().nodename if hasattr(os, "uname") else "localhost",
        "kernel.ostype": "Linux",
        "kernel.osrelease": "5.15.0-91-generic",
        "kernel.pid_max": "4194304",
        "net.ipv4.ip_forward": "0",
        "net.ipv4.tcp_syncookies": "1",
        "net.core.somaxconn": "4096",
        "vm.swappiness": "60",
        "vm.overcommit_memory": "0",
        "fs.file-max": "9223372036854775807",
    }
    if "-a" in args or not args:
        for k, v in fake_params.items():
            console.print(f"{k} = {v}")
    else:
        for a in args:
            if "=" in a:
                k, v = a.split("=", 1)
                console.print(f"{k.strip()} = {v.strip()}")
            elif a in fake_params:
                console.print(f"{a} = {fake_params[a]}")
            else:
                console.print(f"{a} = 0")
    return 0


# ── ldd ──

@register("ldd", "cmd.ldd.help", required_tool="ldd")
def handle_ldd(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: ldd [OPTION]... FILE...\n  Print shared object dependencies")
        return
    console.print(f"\tlinux-vdso.so.1 (0x00007ffd{random.randint(0x1000,0xffff):04x}f000)")
    console.print(f"\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f{random.randint(0x100000,0xffffff):06x})")
    console.print(f"\tlibm.so.6 => /lib/x86_64-linux-gnu/libm.so.6 (0x00007f{random.randint(0x100000,0xffffff):06x})")
    console.print(f"\tlibpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x00007f{random.randint(0x100000,0xffffff):06x})")
    console.print(f"\t/lib64/ld-linux-x86-64.so.2 (0x00007f{random.randint(0x100000,0xffffff):06x})")
    return 0


# ── strace ──

@register("strace", "cmd.strace.help", required_tool="strace")
def handle_strace(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: strace COMMAND [ARGS]\n  Trace system calls and signals")
        return
    cmd = " ".join(args)
    pid = random.randint(1000, 65000)
    console.print(f"execve(\"/usr/bin/{args[0]}\", [\"{args[0]}\"], 0x7fff...) = 0")
    console.print(f"brk(NULL)                               = 0x55{random.randint(0x100000,0xffffff):06x}")
    console.print(f"openat(AT_FDCWD, \"/etc/ld.so.cache\", O_RDONLY|O_CLOEXEC) = 3")
    console.print(f"read(3, \"\\177ELF\\2\\1\\1\\3\\0...\", 832)  = 832")
    console.print(f"close(3)                                = 0")
    from commands.registry import dispatch
    rc = dispatch(game, args)
    console.print(f"write(1, \"...\", {random.randint(10, 500)})  = {random.randint(10, 500)}")
    console.print(f"close(1)                                = 0")
    console.print(f"exit_group({rc or 0})                    = ?")
    console.print(f"+++ exited with {rc or 0} +++")
    return rc


# ── dpkg ──

@register("dpkg", "cmd.dpkg.help", required_tool="dpkg")
def handle_dpkg(game, args):
    if _wants_help(args):
        console.print("Usage: dpkg [OPTIONS]\n  -l  list packages\n  -s PKG  show package status")
        return
    pkgs = [
        ("ii", "base-files", "12ubuntu4", "amd64", "Debian base system miscellaneous files"),
        ("ii", "bash", "5.2.15-2ubuntu1", "amd64", "GNU Bourne Again SHell"),
        ("ii", "coreutils", "9.1-1ubuntu2", "amd64", "GNU core utilities"),
        ("ii", "libc6", "2.38-1ubuntu6", "amd64", "GNU C Library: Shared libraries"),
        ("ii", "openssl", "3.0.10-1ubuntu2", "amd64", "Secure Sockets Layer toolkit"),
        ("ii", "python3", "3.11.4-5", "amd64", "interactive Python interpreter"),
        ("ii", "net-tools", "2.10-0.1ubuntu3", "amd64", "NET-3 networking toolkit"),
        ("ii", "openssh-server", "9.3p1-1ubuntu3", "amd64", "secure shell (SSH) server"),
    ]
    if "-l" in args or not args:
        console.print("Desired=Unknown/Install/Remove/Purge/Hold")
        console.print("| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend")
        console.print("|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)")
        console.print("||/ Name              Version              Architecture Description")
        console.print("+++-=================-====================-============-=================================")
        for st, name, ver, arch, desc in pkgs:
            console.print(f"{st}  {name:18s} {ver:21s} {arch:12s} {desc}")
    elif "-s" in args:
        pkg_name = [a for a in args if a != "-s"]
        pn = pkg_name[0] if pkg_name else "bash"
        console.print(f"Package: {pn}\nStatus: install ok installed\nPriority: required\nSection: shells\nInstalled-Size: 1234\nVersion: 5.2.15-2ubuntu1\nDescription: {pn} package")
    return 0


# ── rsync ──

@register("rsync", "cmd.rsync.help", required_tool="rsync")
def handle_rsync(game, args):
    if _wants_help(args) or len(args) < 2:
        console.print("Usage: rsync [OPTION]... SRC DEST\n  -a  archive mode\n  -v  verbose\n  -z  compress")
        return
    if not _require_host(game): return
    host = game.current_host
    flags = [a for a in args if a.startswith("-")]
    paths = [a for a in args if not a.startswith("-")]
    if len(paths) < 2:
        console.print_error("rsync: need SRC and DEST")
        return 1
    src = _resolve_path(host.cwd, paths[0])
    dst = _resolve_path(host.cwd, paths[1])
    if src not in host.files:
        console.print_error(f"rsync: link_stat \"{src}\" failed: No such file or directory (2)")
        return 1
    host.files[dst] = host.files[src]
    host.user_files[dst] = host.files[dst]
    sz = len(host.files[src].encode())
    console.print(f"sending incremental file list\n{paths[0]}\n\nsent {sz + 100} bytes  received 35 bytes  {sz + 135} bytes/sec\ntotal size is {sz}  speedup is 1.00")
    return 0


# ── cpio ──

@register("cpio", "cmd.cpio.help", required_tool="cpio")
def handle_cpio(game, args):
    console.print("Usage: cpio [OPTION]... [DESTINATION]\n  -i  extract\n  -o  create\n  -t  list\n  -v  verbose\ncpio: requires stdin input in pipeline")
    return 0


# ── patch ──

@register("patch", "cmd.patch.help", required_tool="patch")
def handle_patch(game, args):
    console.print("Usage: patch [OPTION]... [ORIGFILE [PATCHFILE]]\n  -p NUM  strip NUM leading path components\n  -R      reverse patch\n  -b      make backup\npatch: **** No patch file specified")
    return 0


# ── rename ──

@register("rename", "cmd.rename.help", required_tool="rename")
def handle_rename(game, args):
    if _wants_help(args) or len(args) < 2:
        console.print("Usage: rename 's/old/new/' FILES...\n  Rename files using perl expression")
        return
    if not _require_host(game): return
    import re as _re
    host = game.current_host
    expr = args[0]
    files = args[1:]
    m = _re.match(r"s/([^/]*)/([^/]*)/(g?)", expr)
    if not m:
        console.print_error("rename: invalid expression")
        return 1
    old_pat, new_pat = m.group(1), m.group(2)
    count = 0
    for f in files:
        fp = _resolve_path(host.cwd, f)
        if fp in host.files:
            new_name = f.replace(old_pat, new_pat)
            new_fp = _resolve_path(host.cwd, new_name)
            if new_fp != fp:
                host.files[new_fp] = host.files.pop(fp)
                host.user_files[new_fp] = host.files[new_fp]
                console.print(f"{f} -> {new_name}")
                count += 1
    if not count:
        console.print("rename: no files renamed")
    return 0


# ── uuidgen ──

@register("uuidgen", "cmd.uuidgen.help", required_tool="uuidgen")
def handle_uuidgen(game, args):
    if _wants_help(args):
        console.print("Usage: uuidgen [-r]\n  Create a new UUID value")
        return
    import uuid
    console.print(str(uuid.uuid4()))
    return 0


# ── xdg-open ──

@register("xdg-open", "cmd.xdg-open.help", required_tool="xdg-open")
def handle_xdg_open(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: xdg-open {file | URL}\n  Open a file or URL in the preferred application")
        return
    console.print(f"Opening {args[0]} ...")
    return 0


# ── fuser ──

@register("fuser", "cmd.fuser.help", required_tool="fuser")
def handle_fuser(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: fuser [-k] [-n SPACE] NAME\n  Identify processes using files or sockets")
        return
    target = args[-1]
    pid = random.randint(1000, 50000)
    console.print(f"{target}:              {pid}")
    return 0


# ── iconv ──

@register("iconv", "cmd.iconv.help", required_tool="iconv")
def handle_iconv(game, args):
    if _wants_help(args):
        console.print("Usage: iconv [-f FROM] [-t TO] [FILE]\n  Convert encoding of given files")
        return
    data = _get_input(game, args, "iconv")
    if data:
        console.print(data)
    return 0


# ── at ──

@register("at", "cmd.at.help", required_tool="at")
def handle_at(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: at TIME\n  Execute commands at a later time\n  Examples: at now + 5 minutes, at 14:00")
        return
    job_num = random.randint(1, 200)
    time_str = " ".join(args)
    console.print(f"warning: commands will be executed using /bin/sh\njob {job_num} at {time_str}")
    return 0


# ── apropos ──

@register("apropos", "cmd.apropos.help", required_tool="apropos")
def handle_apropos(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: apropos KEYWORD\n  Search the manual page descriptions")
        return
    from commands.registry import COMMANDS
    from ui.lang import t
    keyword = args[0].lower()
    found = False
    for name, (_, help_key, _) in sorted(COMMANDS.items()):
        desc = t(help_key)
        if keyword in name.lower() or keyword in desc.lower():
            console.print(f"{name:20s} - {desc}")
            found = True
    if not found:
        console.print(f"{args[0]}: nothing appropriate.")
    return 0


# ── pv ──

@register("pv", "cmd.pv.help", required_tool="pv")
def handle_pv(game, args):
    if _wants_help(args):
        console.print("Usage: pv [FILE]\n  Monitor the progress of data through a pipe")
        return
    data = _get_input(game, args, "pv")
    if data:
        sz = len(data.encode())
        console.print(data)
        console.print(f" {sz}B 0:00:00 [{sz}B/s] [=====================>] 100%", style="dim")
    return 0


# ── ar ──

@register("ar", "cmd.ar.help", required_tool="ar")
def handle_ar(game, args):
    console.print("Usage: ar [OPTIONS] ARCHIVE [MEMBER...]\n  -r  insert files\n  -t  list contents\n  -x  extract\n  -d  delete\nar: no operation specified")
    return 0


# ── shutdown/reboot/poweroff/halt ──

@register("shutdown", "cmd.shutdown.help", required_tool="shutdown")
def handle_shutdown(game, args):
    if "--help" in args:
        console.print("Usage: shutdown [OPTIONS] [TIME] [MESSAGE]\n  shutdown -h now\n  shutdown -r +5\n  shutdown -c  cancel")
        return
    if "-c" in args:
        console.print("Shutdown cancelled.")
        return 0
    console.print("Shutdown scheduled.")
    console.print("System going down... (simulation only)")
    return 0


# ── gpg ──

@register("gpg", "cmd.gpg.help", required_tool="gpg")
def handle_gpg(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: gpg [OPTIONS] [FILE]\n  gpg --version\n  gpg --gen-key\n  gpg -c file  symmetric encrypt\n  gpg -d file  decrypt\n  gpg --list-keys")
        return
    if args[0] == "--version":
        console.print("gpg (GnuPG) 2.2.27\nlibgcrypt 1.9.4\nCopyright (C) 2021 Free Software Foundation, Inc.")
    elif args[0] == "--list-keys":
        console.print("/home/h/.gnupg/pubring.kbx\n-----------------------------\npub   rsa3072 2024-01-15 [SC]\n      A1B2C3D4E5F6789012345678\nuid           [ultimate] h <h@kali>")
    elif args[0] == "--gen-key":
        console.print("gpg: key generation complete\ngpg: key 0xA1B2C3D4 marked as ultimately trusted")
    else:
        console.print_info("gpg: operation complete")
    return 0


# ── locale ──

@register("locale", "cmd.locale.help", required_tool="locale")
def handle_locale(game, args):
    if _wants_help(args):
        console.print("Usage: locale [-a]\n  locale     show current locale\n  locale -a  list all locales")
        return
    if "-a" in args:
        for loc in ["C", "C.UTF-8", "POSIX", "en_US.utf8", "ru_RU.utf8"]:
            console.print(loc)
    else:
        for k in ["LANG", "LC_CTYPE", "LC_NUMERIC", "LC_TIME", "LC_COLLATE",
                   "LC_MONETARY", "LC_MESSAGES", "LC_ALL"]:
            v = "en_US.UTF-8" if k != "LC_ALL" else ""
            console.print(f"{k}={v}")
    return 0


# ── pidof ──

@register("pidof", "cmd.pidof.help", required_tool="pidof")
def handle_pidof(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: pidof PROGRAM\n  pidof sshd")
        return
    prog = args[-1]
    pid_map = {"sshd": "1234 1235", "bash": "9999", "cron": "1111", "init": "1",
               "systemd": "1", "apache2": "2456 2457", "nginx": "5678 5679"}
    pid = pid_map.get(prog, str(random.randint(1000, 9999)))
    console.print(pid)
    return 0


# ── modprobe / modinfo / lsmod ──

@register("modprobe", "cmd.modprobe.help", required_tool="modprobe")
def handle_modprobe(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: modprobe [OPTIONS] MODULE\n  modprobe module\n  modprobe -r module (remove)")
        return
    if not _require_host(game): return
    if game.current_host.access_level != "root":
        console.print_error("modprobe: Operation not permitted")
        return 1
    console.print_info(f"Module {args[-1]} loaded")
    return 0

@register("modinfo", "cmd.modinfo.help", required_tool="modinfo")
def handle_modinfo(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: modinfo MODULE")
        return
    mod = args[-1]
    console.print(f"filename:       /lib/modules/5.4.0-42-generic/kernel/drivers/{mod}.ko")
    console.print(f"description:    {mod} driver")
    console.print(f"author:         Linux Kernel Contributors")
    console.print(f"license:        GPL")
    console.print(f"srcversion:     {''.join(random.choice('0123456789ABCDEF') for _ in range(16))}")
    return 0


# ── blkid ──

@register("blkid", "cmd.blkid.help", required_tool="blkid")
def handle_blkid(game, args):
    if _wants_help(args):
        console.print("Usage: blkid [device]")
        return
    uid1 = "-".join(f"{''.join(random.choice('0123456789abcdef') for _ in range(s))}" for s in [8,4,4,4,12])
    console.print(f'/dev/sda1: UUID="{uid1}" BLOCK_SIZE="4096" TYPE="ext4" PARTUUID="0001"')
    console.print(f'/dev/sda2: UUID="swap-{random.randint(1000,9999)}" TYPE="swap"')
    return 0


# ── fdisk ──

@register("fdisk", "cmd.fdisk.help", required_tool="fdisk")
def handle_fdisk(game, args):
    if _wants_help(args):
        console.print("Usage: fdisk [OPTIONS] DEVICE\n  fdisk -l       list partitions\n  fdisk /dev/sda  interactive mode")
        return
    if "-l" in args or not args:
        console.print("Disk /dev/sda: 50 GiB, 53687091200 bytes, 104857600 sectors")
        console.print("Device     Boot    Start       End  Sectors  Size Id  Type")
        console.print("/dev/sda1  *        2048  98304000 98301952 46.9G 83  Linux")
        console.print("/dev/sda2       98306048 104857599  6551552  3.1G 82  Linux swap")
    return 0


# ── finger ──

@register("finger", "cmd.finger.help", required_tool="finger")
def handle_finger(game, args):
    if _wants_help(args):
        console.print("Usage: finger [USER]")
        return
    if not _require_host(game): return
    user = args[0] if args else game.current_host.get_current_user()
    console.print(f"Login: {user}\t\t\tName: Pentester")
    console.print(f"Directory: /home/{user}\tShell: /bin/bash")
    console.print(f"Last login: Thu Nov 14 09:15 on pts/0")
    console.print(f"No mail.")
    return 0


# ── timedatectl ──

@register("timedatectl", "cmd.timedatectl.help", required_tool="timedatectl")
def handle_timedatectl(game, args):
    if _wants_help(args):
        console.print("Usage: timedatectl [COMMAND]\n  timedatectl\n  timedatectl set-timezone ZONE")
        return
    import datetime
    now = datetime.datetime.now()
    console.print(f"               Local time: {now.strftime('%a %Y-%m-%d %H:%M:%S UTC')}")
    console.print(f"           Universal time: {now.strftime('%a %Y-%m-%d %H:%M:%S UTC')}")
    console.print(f"                 RTC time: {now.strftime('%a %Y-%m-%d %H:%M:%S')}")
    console.print(f"                Time zone: UTC (UTC, +0000)")
    console.print(f"System clock synchronized: yes")
    console.print(f"              NTP service: active")
    console.print(f"          RTC in local TZ: no")
    return 0


# ── swapon ──

@register("swapon", "cmd.swapon.help", required_tool="swapon")
def handle_swapon(game, args):
    if _wants_help(args):
        console.print("Usage: swapon [OPTIONS] [DEVICE]\n  swapon -s   show summary\n  swapon --show")
        return
    console.print("Filename\t\t\tType\t\tSize\t\tUsed\tPriority")
    console.print(f"/dev/sda2\t\t\tpartition\t{random.randint(2,8)}G\t\t0\t-2")
    return 0


# ── nmcli ──

@register("nmcli", "cmd.nmcli.help", required_tool="nmcli")
def handle_nmcli(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: nmcli [OPTIONS] OBJECT {COMMAND}\n  nmcli device\n  nmcli connection\n  nmcli general status")
        return
    if not _require_host(game): return
    host = game.current_host
    sub = args[0]
    if sub in ("device", "dev", "d"):
        console.print("DEVICE  TYPE      STATE      CONNECTION")
        console.print(f"eth0    ethernet  connected  Wired connection 1")
        console.print(f"lo      loopback  unmanaged  --")
    elif sub in ("connection", "con", "c"):
        console.print("NAME                UUID                                  TYPE      DEVICE")
        console.print(f"Wired connection 1  {''.join(random.choice('0123456789abcdef') for _ in range(32))}  ethernet  eth0")
    elif sub in ("general", "g"):
        console.print("STATE      CONNECTIVITY  WIFI-HW  WIFI  WWAN-HW  WWAN")
        console.print("connected  full          enabled  N/A   enabled  N/A")
    return 0


# ── runlevel ──

@register("runlevel", "cmd.runlevel.help", required_tool="runlevel")
def handle_runlevel(game, args):
    console.print("N 5")
    return 0
