"""Shell built-ins: export, unset, set, alias, unalias, type, source, exit, sleep, test, read, kill, killall, find."""
import time
import re
import fnmatch
import random
from commands.registry import register
from commands.linux_cmds import _require_host, _wants_help
from ui.console import console
from ui.lang import t


# -----------------------------------------------------------------------
# export
# -----------------------------------------------------------------------
@register("export", "cmd.export.help", required_tool="export")
def handle_export(game, args):
    if _wants_help(args):
        console.print("Usage: export [NAME[=VALUE]]...\n")
        console.print("  export VAR=value   set and export variable")
        console.print("  export -p          show all exported variables")
        return
    if not _require_host(game):
        return
    if not args or "-p" in args:
        for k, v in game.current_host.env.items():
            console.print(f"declare -x {k}=\"{v}\"")
        return
    for arg in args:
        if "=" in arg:
            key, val = arg.split("=", 1)
            val = val.strip("'\"")
            game.current_host.env[key] = val
        else:
            # export existing shell var
            if arg in game.shell_vars:
                game.current_host.env[arg] = game.shell_vars[arg]


# -----------------------------------------------------------------------
# unset
# -----------------------------------------------------------------------
@register("unset", "cmd.unset.help", required_tool="unset")
def handle_unset(game, args):
    if _wants_help(args):
        console.print("Usage: unset NAME...\n")
        console.print("  unset VAR     remove environment variable")
        return
    if not _require_host(game):
        return
    for name in args:
        game.current_host.env.pop(name, None)
        game.shell_vars.pop(name, None)


# -----------------------------------------------------------------------
# set
# -----------------------------------------------------------------------
@register("set", "cmd.set.help", required_tool="set")
def handle_set(game, args):
    if _wants_help(args):
        console.print("Usage: set [OPTION]\n")
        console.print("  set            show all shell variables")
        console.print("  set -e         exit on error")
        console.print("  set -x         print commands before executing")
        return
    if not _require_host(game):
        return
    if not args:
        for k, v in game.current_host.env.items():
            console.print(f"{k}={v}")
        for k, v in game.shell_vars.items():
            console.print(f"{k}={v}")
        return


# -----------------------------------------------------------------------
# alias / unalias
# -----------------------------------------------------------------------
@register("alias", "cmd.alias.help", required_tool="alias")
def handle_alias(game, args):
    if _wants_help(args):
        console.print("Usage: alias [NAME[=VALUE]]...\n")
        console.print("  alias                 show all aliases")
        console.print("  alias ll='ls -lah'    create alias")
        return
    if not args:
        for name, value in game.aliases.items():
            console.print(f"alias {name}='{value}'")
        return
    for arg in args:
        if "=" in arg:
            name, value = arg.split("=", 1)
            game.aliases[name] = value.strip("'\"")
        else:
            if arg in game.aliases:
                console.print(f"alias {arg}='{game.aliases[arg]}'")
            else:
                console.print_error(f"alias: {arg}: not found")


@register("unalias", "cmd.unalias.help", required_tool="unalias")
def handle_unalias(game, args):
    if _wants_help(args):
        console.print("Usage: unalias NAME...\n")
        console.print("  unalias ll    remove alias")
        console.print("  unalias -a    remove all aliases")
        return
    if "-a" in args:
        game.aliases.clear()
        return
    for name in args:
        if name in game.aliases:
            del game.aliases[name]


# -----------------------------------------------------------------------
# type
# -----------------------------------------------------------------------
@register("type", "cmd.type.help", required_tool="type")
def handle_type(game, args):
    if _wants_help(args):
        console.print("Usage: type NAME...\n")
        console.print("  type ls      show whether builtin, alias, or file")
        return
    from commands.registry import COMMANDS
    for name in args:
        if name in game.aliases:
            console.print(f"{name} is aliased to '{game.aliases[name]}'")
        elif name in COMMANDS:
            console.print(f"{name} is a shell builtin")
        elif game.current_host:
            found = False
            for prefix in ["/usr/bin", "/usr/sbin", "/bin", "/sbin"]:
                path = f"{prefix}/{name}"
                if path in game.current_host.files:
                    console.print(f"{name} is {path}")
                    found = True
                    break
            if not found:
                console.print_error(f"-bash: type: {name}: not found")
                return 1
        else:
            console.print_error(f"-bash: type: {name}: not found")
            return 1
    return 0


# -----------------------------------------------------------------------
# exit
# -----------------------------------------------------------------------
@register("exit", "cmd.exit.help", required_tool="exit")
def handle_exit(game, args):
    if game.is_on_localhost():
        console.print()
        console.print(f"[bold green]{t('quit.thanks')}[/bold green]")
        console.print(f"[dim]{t('quit.motto')}[/dim]")
        console.print()
        game.running = False
    else:
        # Exit from remote host = disconnect
        ip = game.current_host.ip
        game.return_to_localhost()
        console.print_info(t("disconnect.done", ip=ip))


# -----------------------------------------------------------------------
# sleep
# -----------------------------------------------------------------------
@register("sleep", "cmd.sleep.help", required_tool="sleep")
def handle_sleep(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: sleep NUMBER[SUFFIX]\n")
        console.print("  sleep 5      pause for 5 seconds")
        console.print("  sleep 0.5    pause for 0.5 seconds")
        return
    try:
        duration = float(args[0].rstrip("s"))
        duration = min(duration, 30)  # cap at 30s for game
        time.sleep(duration)
    except ValueError:
        console.print_error(f"sleep: invalid time interval '{args[0]}'")


# -----------------------------------------------------------------------
# kill
# -----------------------------------------------------------------------
@register("kill", "cmd.kill.help", required_tool="kill")
def handle_kill(game, args):
    if _wants_help(args):
        console.print("Usage: kill [OPTION] PID...\n")
        console.print("  kill PID          send SIGTERM to process")
        console.print("  kill -9 PID       send SIGKILL (force kill)")
        console.print("  kill -l           list signal names")
        return
    if "-l" in args:
        signals = ["HUP", "INT", "QUIT", "ILL", "TRAP", "ABRT", "BUS", "FPE",
                    "KILL", "USR1", "SEGV", "USR2", "PIPE", "ALRM", "TERM",
                    "STKFLT", "CHLD", "CONT", "STOP", "TSTP"]
        for i, sig in enumerate(signals, 1):
            console.print(f"{i:2d}) SIG{sig}", end="  ")
            if i % 5 == 0:
                console.print()
        console.print()
        return
    pids = [a for a in args if not a.startswith("-")]
    if not pids:
        console.print_error("kill: missing operand")
        return
    for pid in pids:
        console.print(f"[dim]kill: sent signal to process {pid}[/dim]")


# -----------------------------------------------------------------------
# killall
# -----------------------------------------------------------------------
@register("killall", "cmd.killall.help", required_tool="killall")
def handle_killall(game, args):
    if _wants_help(args):
        console.print("Usage: killall [OPTION] NAME...\n")
        console.print("  killall nginx     kill all nginx processes")
        console.print("  killall -9 sshd   force kill")
        return
    names = [a for a in args if not a.startswith("-")]
    if not names:
        console.print_error("killall: missing operand")
        return
    for name in names:
        console.print(f"[dim]killall: killed processes matching '{name}'[/dim]")


# -----------------------------------------------------------------------
# find
# -----------------------------------------------------------------------
@register("find", "cmd.find.help", required_tool="find")
def handle_find(game, args):
    if _wants_help(args):
        console.print("Usage: find [PATH] [EXPRESSION]\n")
        console.print("  find / -name '*.conf'       find by name")
        console.print("  find /etc -type f            find files only")
        console.print("  find / -name '*.log' -type f")
        console.print("  find . -maxdepth 2 -name '*.txt'")
        return
    if not _require_host(game):
        return

    host = game.current_host
    from commands.filesystem_cmds import _resolve_path

    # Parse args
    search_path = host.cwd
    name_pattern = None
    type_filter = None
    max_depth = 999
    exec_cmd = None
    size_filter = None
    user_filter = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "-name" and i + 1 < len(args):
            name_pattern = args[i + 1]
            i += 2
        elif a == "-iname" and i + 1 < len(args):
            name_pattern = args[i + 1]  # handled with case-insensitive below
            i += 2
        elif a == "-type" and i + 1 < len(args):
            type_filter = args[i + 1]
            i += 2
        elif a == "-maxdepth" and i + 1 < len(args):
            try:
                max_depth = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif a == "-user" and i + 1 < len(args):
            user_filter = args[i + 1]
            i += 2
        elif a == "-size" and i + 1 < len(args):
            size_filter = args[i + 1]
            i += 2
        elif a == "-exec":
            # Collect everything until \; or ;
            exec_parts = []
            i += 1
            while i < len(args) and args[i] not in (";", "\\;"):
                exec_parts.append(args[i])
                i += 1
            exec_cmd = " ".join(exec_parts)
            i += 1  # skip the ;
        elif a == "-prune":
            i += 1
        elif not a.startswith("-"):
            search_path = a if a.startswith("/") else _resolve_path(host.cwd, a)
            i += 1
        else:
            i += 1

    # Determine case-insensitive name matching
    iname = any(a == "-iname" for a in args)

    # Search filesystem
    prefix = search_path.rstrip("/") + "/" if search_path != "/" else "/"
    from engine.shell import process_line

    found_any = False
    for filepath in sorted(host.files.keys()):
        if not filepath.startswith(prefix) and filepath != search_path:
            continue

        # Check depth
        rel = filepath[len(prefix):]
        depth = rel.count("/") + 1
        if depth > max_depth:
            continue

        filename = filepath.split("/")[-1]

        # Name filter
        if name_pattern:
            if iname:
                if not fnmatch.fnmatch(filename.lower(), name_pattern.lower()):
                    continue
            else:
                if not fnmatch.fnmatch(filename, name_pattern):
                    continue

        # Type filter
        if type_filter:
            is_dir = any(f.startswith(filepath + "/") for f in host.files if f != filepath)
            if type_filter == "f" and is_dir:
                continue
            if type_filter == "d" and not is_dir:
                continue

        # User filter
        if user_filter:
            meta = host.file_meta.get(filepath, {})
            if meta.get("owner", "root") != user_filter:
                continue

        found_any = True
        if exec_cmd:
            # Replace {} with filepath
            cmd = exec_cmd.replace("{}", filepath)
            process_line(cmd)
        else:
            console.print(filepath)

    return 0 if found_any else 1


# -----------------------------------------------------------------------
# read
# -----------------------------------------------------------------------
@register("read", "cmd.read.help", required_tool="read")
def handle_read(game, args):
    if _wants_help(args):
        console.print("Usage: read [OPTION] NAME...\n")
        console.print("  read VAR           read a line into VAR")
        console.print("  read -p 'prompt' VAR   show prompt")
        return
    if not _require_host(game):
        return

    prompt_text = ""
    var_name = "REPLY"

    i = 0
    while i < len(args):
        if args[i] == "-p" and i + 1 < len(args):
            prompt_text = args[i + 1]
            i += 2
        elif not args[i].startswith("-"):
            var_name = args[i]
            i += 1
        else:
            i += 1

    try:
        if prompt_text:
            value = console.input(prompt_text + " ")
        else:
            value = console.input("")
    except (EOFError, KeyboardInterrupt):
        value = ""

    game.current_host.env[var_name] = value.strip()


# -----------------------------------------------------------------------
# test / [
# -----------------------------------------------------------------------
@register("test", "cmd.test.help", required_tool="test")
def handle_test(game, args):
    if _wants_help(args):
        console.print("Usage: test EXPRESSION\n")
        console.print("  test -f file     true if file exists and is regular")
        console.print("  test -d dir      true if dir exists")
        console.print("  test -e path     true if path exists")
        console.print("  test -z string   true if string is empty")
        console.print("  test -n string   true if string is not empty")
        console.print("  test a = b       string equality")
        console.print("  test 5 -gt 3     numeric comparison")
        return
    if not _require_host(game):
        return
    return 0 if _eval_test(game, args) else 1


@register("[", "cmd.test.help", required_tool="[")
def handle_bracket(game, args):
    # Remove trailing ]
    if args and args[-1] == "]":
        args = args[:-1]
    return handle_test(game, args)


def _eval_test(game, args) -> bool:
    if not args:
        return False
    host = game.current_host
    from commands.filesystem_cmds import _resolve_path

    if len(args) == 1:
        return len(args[0]) > 0  # -n equivalent

    if args[0] == "-f":
        path = args[1] if args[1].startswith("/") else _resolve_path(host.cwd, args[1])
        return path in host.files
    if args[0] == "-d":
        path = args[1] if args[1].startswith("/") else _resolve_path(host.cwd, args[1])
        prefix = path.rstrip("/") + "/"
        return any(f.startswith(prefix) for f in host.files)
    if args[0] == "-e":
        path = args[1] if args[1].startswith("/") else _resolve_path(host.cwd, args[1])
        prefix = path.rstrip("/") + "/"
        return path in host.files or any(f.startswith(prefix) for f in host.files)
    if args[0] == "-z":
        return len(args[1]) == 0
    if args[0] == "-n":
        return len(args[1]) > 0
    if args[0] == "-r" or args[0] == "-w" or args[0] == "-x":
        path = args[1] if args[1].startswith("/") else _resolve_path(host.cwd, args[1])
        return path in host.files
    if args[0] == "!":
        return not _eval_test(game, args[1:])

    if len(args) == 3:
        left, op, right = args
        if op == "=" or op == "==":
            return left == right
        if op == "!=":
            return left != right
        try:
            l, r = int(left), int(right)
            if op == "-eq": return l == r
            if op == "-ne": return l != r
            if op == "-gt": return l > r
            if op == "-ge": return l >= r
            if op == "-lt": return l < r
            if op == "-le": return l <= r
        except ValueError:
            pass

    return False


# -----------------------------------------------------------------------
# systemctl
# -----------------------------------------------------------------------
@register("systemctl", "cmd.systemctl.help", required_tool="systemctl")
def handle_systemctl(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: systemctl COMMAND [UNIT]\n")
        console.print("  systemctl status sshd      check service status")
        console.print("  systemctl start nginx      start service")
        console.print("  systemctl stop mysql       stop service")
        console.print("  systemctl restart sshd     restart service")
        console.print("  systemctl enable sshd      enable at boot")
        console.print("  systemctl list-units       list all units")
        return
    if not _require_host(game):
        return

    subcmd = args[0]
    unit = args[1] if len(args) > 1 else None
    host = game.current_host

    if subcmd == "list-units":
        console.print(f"{'UNIT':30s} {'LOAD':10s} {'ACTIVE':10s} {'SUB':10s} {'DESCRIPTION'}")
        for svc in host.services:
            console.print(f"{svc.name + '.service':30s} {'loaded':10s} {'active':10s} {'running':10s} {svc.name} service")
        console.print(f"{'cron.service':30s} {'loaded':10s} {'active':10s} {'running':10s} Regular background program processing daemon")
        console.print(f"{'rsyslog.service':30s} {'loaded':10s} {'active':10s} {'running':10s} System Logging Service")
        return

    if not unit:
        console.print_error(f"systemctl: missing unit name")
        return

    # Normalize unit name
    unit_name = unit.replace(".service", "")

    if subcmd == "status":
        # Check if service exists
        svc = host.get_service_by_name(unit_name)
        if svc:
            pid = random.randint(800, 5000)
            console.print(f"● {unit_name}.service - {unit_name} service")
            console.print(f"     Loaded: loaded (/lib/systemd/system/{unit_name}.service; enabled)")
            console.print(f"     Active: [green]active (running)[/green] since Fri 2024-11-15 14:30:02 UTC")
            console.print(f"   Main PID: {pid} ({unit_name})")
            console.print(f"      Tasks: {random.randint(1, 10)}")
            console.print(f"     Memory: {random.randint(1, 200)}M")
            console.print(f"        CPU: {random.randint(0, 50)}ms")
        else:
            console.print(f"● {unit_name}.service")
            console.print(f"     Loaded: not-found")
            console.print(f"     Active: [red]inactive (dead)[/red]")
            return 1
    elif subcmd in ("start", "restart", "reload"):
        if host.access_level != "root":
            console.print_error(f"Failed to {subcmd} {unit_name}.service: Access denied")
            return 1
        console.print(f"[dim]{unit_name}.service {subcmd}ed[/dim]")
    elif subcmd == "stop":
        if host.access_level != "root":
            console.print_error(f"Failed to stop {unit_name}.service: Access denied")
            return 1
        console.print(f"[dim]{unit_name}.service stopped[/dim]")
    elif subcmd in ("enable", "disable"):
        if host.access_level != "root":
            console.print_error(f"Failed to {subcmd} {unit_name}.service: Access denied")
            return 1
        console.print(f"[dim]{unit_name}.service {subcmd}d[/dim]")
    elif subcmd == "is-active":
        svc = host.get_service_by_name(unit_name)
        console.print("active" if svc else "inactive")
        return 0 if svc else 1
    else:
        console.print_error(f"systemctl: unknown command '{subcmd}'")
        return 1
    return 0


@register("service", "cmd.service.help", required_tool="service")
def handle_service(game, args):
    if _wants_help(args) or len(args) < 2:
        console.print("Usage: service NAME COMMAND\n")
        console.print("  service sshd status     check status")
        console.print("  service nginx start     start service")
        return
    # Remap to systemctl
    name = args[0]
    action = args[1]
    return handle_systemctl(game, [action, name])


# -----------------------------------------------------------------------
# dmesg
# -----------------------------------------------------------------------
@register("dmesg", "cmd.dmesg.help", required_tool="dmesg")
def handle_dmesg(game, args):
    if _wants_help(args):
        console.print("Usage: dmesg [OPTIONS]\n")
        console.print("  dmesg           show kernel messages")
        console.print("  dmesg | tail    show last messages")
        return
    if not _require_host(game):
        return
    host = game.current_host
    kernel = "5.4.0-42-generic" if "20" in host.os else "5.15.0-91-generic"
    msgs = [
        f"[    0.000000] Linux version {kernel} (buildd@lgw01) (gcc version 9.3.0)",
        f"[    0.000000] Command line: BOOT_IMAGE=/vmlinuz-{kernel} root=UUID=a1b2c3d4 ro quiet splash",
        "[    0.000000] BIOS-provided physical RAM map:",
        "[    0.000000]  BIOS-e820: [mem 0x0000000000000000-0x000000000009fbff] usable",
        "[    0.004321] NX (Execute Disable) protection: active",
        "[    0.052109] Booting paravirtualized kernel on bare hardware",
        f"[    0.100000] Hostname: {host.hostname}",
        "[    1.234567] EXT4-fs (sda1): mounted filesystem with ordered data mode.",
        "[    1.500000] systemd[1]: systemd 245 running in system mode.",
        f"[    2.000000] net eth0: registered device, IP {host.ip}",
    ]
    for svc in host.services:
        msgs.append(f"[    2.{random.randint(100,999)}] {svc.name}: service started on port {svc.port}")
    for msg in msgs:
        console.print(msg)


# -----------------------------------------------------------------------
# journalctl
# -----------------------------------------------------------------------
@register("journalctl", "cmd.journalctl.help", required_tool="journalctl")
def handle_journalctl(game, args):
    if _wants_help(args):
        console.print("Usage: journalctl [OPTIONS]\n")
        console.print("  journalctl          show all logs")
        console.print("  journalctl -e       jump to end")
        console.print("  journalctl -u sshd  show logs for unit")
        console.print("  journalctl -n 20    show last 20 lines")
        return
    if not _require_host(game):
        return

    host = game.current_host
    n = 20
    unit = None
    if "-n" in args:
        idx = args.index("-n")
        if idx + 1 < len(args):
            try:
                n = int(args[idx + 1])
            except ValueError:
                pass
    if "-u" in args:
        idx = args.index("-u")
        if idx + 1 < len(args):
            unit = args[idx + 1]

    # Read syslog
    syslog = host.files.get("/var/log/syslog", "")
    lines = syslog.strip().split("\n") if syslog.strip() else []

    if unit:
        lines = [l for l in lines if unit in l.lower()]

    for line in lines[-n:]:
        console.print(line)


# -----------------------------------------------------------------------
# source / .
# -----------------------------------------------------------------------
@register("source", "cmd.source.help", required_tool="source")
def handle_source(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: source FILE [ARGS]\n  Execute commands from FILE in the current shell.")
        return
    if not _require_host(game):
        return
    from commands.filesystem_cmds import _resolve_path
    filepath = args[0] if args[0].startswith("/") else _resolve_path(game.current_host.cwd, args[0])
    if filepath not in game.current_host.files:
        console.print_error(f"source: {filepath}: No such file or directory")
        return 1
    content = game.current_host.files[filepath]
    from engine.shell import process_line
    for line in content.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            process_line(line)
    return 0

@register(".", "cmd.source.help", required_tool="source")
def handle_dot_source(game, args):
    return handle_source(game, args)


# -----------------------------------------------------------------------
# eval
# -----------------------------------------------------------------------
@register("eval", "cmd.eval.help", required_tool="eval")
def handle_eval(game, args):
    if _wants_help(args):
        console.print("Usage: eval [ARGS]\n  Evaluate ARGS as a shell command.")
        return
    if not args:
        return 0
    from engine.shell import process_line
    process_line(" ".join(args))
    return 0


# -----------------------------------------------------------------------
# expr
# -----------------------------------------------------------------------
@register("expr", "cmd.expr.help", required_tool="expr")
def handle_expr(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: expr EXPRESSION\n  expr 1 + 2\n  expr 10 \\* 3\n  expr length STRING")
        return
    # length
    if len(args) >= 2 and args[0] == "length":
        console.print(str(len(args[1])))
        return 0
    # substr
    if len(args) >= 4 and args[0] == "substr":
        s = args[1]
        try:
            pos = int(args[2]) - 1
            length = int(args[3])
            console.print(s[pos:pos + length])
        except (ValueError, IndexError):
            console.print_error("expr: syntax error")
            return 2
        return 0
    # Arithmetic: join all args and eval
    expr_str = " ".join(args).replace("*", "*")
    # Make it safe: only digits, operators, spaces, parens
    sanitized = re.sub(r'[^0-9+\-*/%() ]', '', expr_str)
    try:
        result = eval(sanitized)
        console.print(str(int(result)))
        return 0 if result != 0 else 1  # expr returns 1 for 0
    except Exception:
        console.print_error("expr: syntax error")
        return 2


# -----------------------------------------------------------------------
# let
# -----------------------------------------------------------------------
@register("let", "cmd.let.help", required_tool="let")
def handle_let(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: let EXPRESSION\n  let x=5\n  let x=x+1\n  let 'x += 3'")
        return
    if not _require_host(game):
        return
    env = game.current_host.env
    for expr in args:
        # Parse assignment: var=expr or var+=expr
        m = re.match(r'(\w+)\s*(\+?=)\s*(.*)', expr)
        if m:
            var = m.group(1)
            op = m.group(2)
            val_str = m.group(3)
            # Resolve variables in the value
            for v in re.findall(r'\b([A-Za-z_]\w*)\b', val_str):
                if v in env:
                    val_str = val_str.replace(v, env[v])
                elif v in game.shell_vars:
                    val_str = val_str.replace(v, str(game.shell_vars[v]))
            sanitized = re.sub(r'[^0-9+\-*/%() ]', '', val_str)
            try:
                val = int(eval(sanitized))
            except Exception:
                val = 0
            if op == "+=" and var in env:
                try:
                    val = int(env[var]) + val
                except ValueError:
                    pass
            env[var] = str(val)
            game.shell_vars[var] = str(val)
    return 0


# -----------------------------------------------------------------------
# timeout
# -----------------------------------------------------------------------
@register("timeout", "cmd.timeout.help", required_tool="timeout")
def handle_timeout(game, args):
    if _wants_help(args) or len(args) < 2:
        console.print("Usage: timeout DURATION COMMAND [ARGS]\n  timeout 5 ping host\n  timeout 10s command")
        return
    # Skip the duration, just execute the command
    from engine.shell import process_line
    cmd = " ".join(args[1:])
    process_line(cmd)
    return 0


# -----------------------------------------------------------------------
# pgrep / pkill
# -----------------------------------------------------------------------
@register("pgrep", "cmd.pgrep.help", required_tool="pgrep")
def handle_pgrep(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: pgrep [OPTIONS] PATTERN\n  pgrep ssh\n  pgrep -u root\n  pgrep -f 'python script'")
        return
    if not _require_host(game):
        return
    pattern = args[-1]
    show_full = "-f" in args
    # Generate fake matching processes
    fake_procs = {
        "ssh": [(1234, "sshd"), (1235, "/usr/sbin/sshd -D")],
        "apache": [(2456, "apache2"), (2457, "apache2 -k start")],
        "mysql": [(3456, "mysqld"), (3457, "/usr/sbin/mysqld --basedir=/usr")],
        "python": [(4567, "python3"), (4568, "python3 /opt/app/server.py")],
        "nginx": [(5678, "nginx: master"), (5679, "nginx: worker")],
        "cron": [(1111, "cron"), (1112, "/usr/sbin/cron -f")],
        "bash": [(9999, "-bash")],
    }
    found = False
    for key, procs in fake_procs.items():
        if pattern.lower() in key:
            for pid, cmd in procs:
                if show_full:
                    console.print(f"{pid} {cmd}")
                else:
                    console.print(str(pid))
            found = True
    return 0 if found else 1


@register("pkill", "cmd.pkill.help", required_tool="pkill")
def handle_pkill(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: pkill [OPTIONS] PATTERN\n  pkill ssh\n  pkill -9 process\n  pkill -u user")
        return
    if not _require_host(game):
        return
    pattern = args[-1]
    console.print_info(f"Processes matching '{pattern}' terminated")
    return 0


# -----------------------------------------------------------------------
# host (DNS lookup)
# -----------------------------------------------------------------------
@register("host", "cmd.host.help", required_tool="host")
def handle_host(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: host [OPTIONS] NAME [SERVER]\n  host example.com\n  host -t MX example.com")
        return
    record_type = None
    target = args[-1]
    if "-t" in args:
        idx = args.index("-t")
        if idx + 1 < len(args):
            record_type = args[idx + 1].upper()
            target = args[-1] if args[-1] != record_type else args[-1]
    # Generate realistic DNS responses
    ip = f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    console.print(f"{target} has address {ip}")
    if record_type == "MX" or not record_type:
        if not record_type:
            console.print(f"{target} mail is handled by 10 mail.{target}")
    if record_type == "MX":
        console.print(f"{target} mail is handled by 10 mail.{target}")
        console.print(f"{target} mail is handled by 20 mail2.{target}")
    elif record_type == "NS":
        console.print(f"{target} name server ns1.{target}")
        console.print(f"{target} name server ns2.{target}")
    elif record_type == "AAAA":
        console.print(f"{target} has IPv6 address 2606:2800:220:1:248:1893:25c8:1946")
    elif record_type == "TXT":
        console.print(f'{target} descriptive text "v=spf1 include:_spf.{target} ~all"')
    return 0


# -----------------------------------------------------------------------
# ssh-keygen
# -----------------------------------------------------------------------
@register("ssh-keygen", "cmd.ssh-keygen.help", required_tool="ssh-keygen")
def handle_ssh_keygen(game, args):
    if _wants_help(args):
        console.print("Usage: ssh-keygen [OPTIONS]\n  ssh-keygen -t rsa -b 4096\n  ssh-keygen -t ed25519\n  ssh-keygen -f keyfile")
        return
    if not _require_host(game):
        return
    key_type = "rsa"
    bits = 3072
    output_file = f"/home/{game.current_host.get_current_user()}/.ssh/id_rsa"
    i = 0
    while i < len(args):
        if args[i] == "-t" and i + 1 < len(args):
            key_type = args[i + 1]
            i += 2
        elif args[i] == "-b" and i + 1 < len(args):
            try:
                bits = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "-f" and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        else:
            i += 1

    if key_type == "ed25519":
        bits = 256
    pub_file = output_file + ".pub"

    console.print(f"Generating public/private {key_type} key pair.")
    console.print(f"Your identification has been saved in {output_file}")
    console.print(f"Your public key has been saved in {pub_file}")
    fingerprint = ":".join(f"{random.randint(0,255):02x}" for _ in range(16))
    console.print(f"The key fingerprint is:")
    console.print(f"SHA256:{fingerprint}")
    user = game.current_host.get_current_user()
    console.print(f"The key's randomart image is:")
    console.print("+---[{} {}]----+".format(key_type.upper(), bits))
    for _ in range(9):
        inner = "".join(random.choice(" .o+=*BOX@%&#/^SE") for _ in range(17))
        console.print(f"|{inner}|")
    console.print("+----[SHA256]-----+")

    # Create the key files in the virtual filesystem
    import string
    priv_key = f"-----BEGIN {key_type.upper()} PRIVATE KEY-----\n"
    for _ in range(5):
        priv_key += "".join(random.choice(string.ascii_letters + string.digits + "+/") for _ in range(64)) + "\n"
    priv_key += f"-----END {key_type.upper()} PRIVATE KEY-----\n"
    pub_key = f"ssh-{key_type} {''.join(random.choice(string.ascii_letters + string.digits + '+/') for _ in range(80))} {user}@{game.current_host.hostname}"

    game.current_host.files[output_file] = priv_key
    game.current_host.files[pub_file] = pub_key
    game.current_host.file_meta[output_file] = {"perms": "-rw-------", "owner": user, "group": user, "mtime": "May 22 15:30"}
    game.current_host.file_meta[pub_file] = {"perms": "-rw-r--r--", "owner": user, "group": user, "mtime": "May 22 15:30"}
    game.current_host.user_files[output_file] = priv_key
    game.current_host.user_files[pub_file] = pub_key
    return 0
