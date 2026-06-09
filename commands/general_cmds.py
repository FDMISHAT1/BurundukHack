from commands.registry import register, COMMANDS
from ui.console import console
from ui.lang import t
from ui import banners


@register("help", "cmd.help.help", required_tool="help")
def handle_help(game, args):
    if args:
        cmd_name = args[0].lower()
        if cmd_name in COMMANDS:
            _, help_key, req_tool = COMMANDS[cmd_name]
            console.print(f"  [bold green]{cmd_name}[/bold green] — {t(help_key)}")
            if req_tool and req_tool not in game.player.tools_unlocked:
                console.print(f"  [dim red]({t('help.locked_full')})[/dim red]")
        else:
            console.print_error(t("help.unknown_cmd", cmd=cmd_name))
        return

    console.print()
    console.print(f"[bold bright_white]{t('help.available')}:[/bold bright_white]")
    console.print()

    categories = {
        "help.cat_recon": ["nmap", "ping"],
        "help.cat_access": ["ssh", "disconnect", "exploit", "crack", "sudo", "su"],
        "help.cat_filesystem": ["ls", "cd", "cat", "head", "tail", "grep", "wc",
                               "touch", "mkdir", "rmdir", "rm", "cp", "mv", "ln",
                               "nano", "download", "readlink", "realpath", "basename",
                               "dirname", "stat", "du", "shred", "less", "more",
                               "tree", "dd", "rename", "rsync"],
        "help.cat_text": ["sort", "uniq", "cut", "tr", "sed", "awk",
                          "tee", "xargs", "rev", "seq"],
        "help.cat_linux": ["whoami", "pwd", "id", "uname", "hostname", "ps", "env",
                           "echo", "which", "date", "uptime", "free", "df", "mount",
                           "chmod", "man", "history"],
        "help.cat_network": ["ifconfig", "ip", "netstat", "ss"],
        "help.cat_nettools": ["wget", "nc", "dig", "nslookup", "traceroute",
                              "iptables", "scp", "whois", "host", "ssh-keygen",
                              "telnet", "arp", "tcpdump"],
        "help.cat_forensics": ["strings", "xxd", "file", "base64", "md5sum",
                               "sha256sum", "binwalk", "steghide", "exiftool", "curl",
                               "openssl"],
        "help.cat_packages": ["apt"],
        "help.cat_shell": ["export", "unset", "set", "alias", "unalias", "type",
                           "read", "test", "sleep", "exit", "true", "false",
                           "nohup", "yes", "source", "eval", "expr", "let",
                           "timeout", "jobs", "bg", "fg", "trap", "wait",
                           "screen", "tmux", "logger", "wall", "time", "umask"],
        "help.cat_sysadmin": ["systemctl", "service", "journalctl", "dmesg",
                              "kill", "killall", "find", "top", "lsblk", "lsof",
                              "crontab", "chown", "chgrp", "passwd", "useradd",
                              "groupadd", "w", "who", "users", "last", "mktemp",
                              "pgrep", "pkill", "usermod", "userdel", "getent",
                              "locate", "whereis",
                              "lscpu", "lsusb", "lspci", "vmstat", "nice", "renice",
                              "htop", "chroot", "ulimit", "sysctl", "ldd",
                              "strace", "dpkg", "fuser", "at",
                              "shutdown", "modprobe", "modinfo", "blkid", "fdisk",
                              "swapon", "timedatectl", "nmcli", "runlevel",
                              "pidof", "locale", "finger", "gpg"],
        "help.cat_archive": ["tar", "zip", "unzip", "gzip", "gunzip", "bzip2", "xz",
                             "cpio", "ar"],
        "help.cat_textutil": ["diff", "printf", "column", "od", "nl", "tac",
                              "paste", "comm", "hexdump", "expand", "unexpand",
                              "cal", "bc", "dc", "watch", "stty", "fold", "fmt",
                              "join", "split", "tput", "mkfifo", "truncate", "install",
                              "uuidgen", "xdg-open", "iconv", "apropos", "pv",
                              "patch"],
        "help.cat_dev": ["git", "python3", "gcc", "make"],
        "help.cat_info": ["help", "status", "missions", "hint"],
        "help.cat_system": ["clear", "reset", "quit"],
    }

    for cat_key, cmds in categories.items():
        console.print(f"  [bold cyan]{t(cat_key)}:[/bold cyan]")
        for cmd_name in cmds:
            if cmd_name in COMMANDS:
                _, help_key, req_tool = COMMANDS[cmd_name]
                if req_tool and req_tool not in game.player.tools_unlocked:
                    console.print(f"    [dim]{cmd_name:12s} [{t('help.locked')}][/dim]")
                else:
                    console.print(f"    [green]{cmd_name:12s}[/green] {t(help_key)}")
        console.print()


@register("status", "cmd.status.help", required_tool="status")
def handle_status(game, args):
    console.print()
    console.print(f"  [bold cyan]{t('status.handle')}:[/bold cyan]     {game.player.handle}")
    console.print(f"  [bold cyan]{t('status.reputation')}:[/bold cyan] {game.player.reputation}")

    if game.current_host:
        console.print(f"  [bold cyan]{t('status.connected')}:[/bold cyan] {game.current_host.ip} ({game.current_host.hostname})")
        console.print(f"  [bold cyan]{t('status.access')}:[/bold cyan]    {game.current_host.access_level}")
    else:
        console.print(f"  [bold cyan]{t('status.connected')}:[/bold cyan] localhost")

    if game.current_mission:
        done = sum(1 for o in game.current_mission.objectives if o.completed)
        total = len(game.current_mission.objectives)
        console.print(f"  [bold cyan]{t('status.mission')}:[/bold cyan]   {game.current_mission.title} [{done}/{total}]")

    if game.player.known_credentials:
        console.print()
        console.print(f"  [bold cyan]{t('status.known_creds')}:[/bold cyan]")
        for cred in game.player.known_credentials:
            console.print(f"    {cred['username']}:{cred['password']} @ {cred['host']}")
    console.print()


@register("missions", "cmd.missions.help", required_tool="missions")
def handle_missions(game, args):
    if not game.current_mission:
        console.print_warning(t("missions.no_active"))
        return

    banners.show_mission_briefing(
        game.current_mission.title,
        game.current_mission.briefing,
        game.current_mission.objectives,
    )


@register("hint", "cmd.hint.help", required_tool="hint")
def handle_hint(game, args):
    if not game.current_mission:
        console.print_warning(t("missions.no_active"))
        return

    hint = game.current_mission.get_next_hint()
    if hint:
        console.print()
        console.print_panel("HINT", hint, style="yellow")
    else:
        console.print_warning(t("missions.no_hints"))


@register("clear", "cmd.clear.help", required_tool="clear")
def handle_clear(game, args):
    console.console.clear()


@register("quit", "cmd.quit.help", required_tool="quit")
def handle_quit(game, args):
    console.print()
    console.print(f"[bold green]{t('quit.thanks')}[/bold green]")
    console.print(f"[dim]{t('quit.motto')}[/dim]")
    console.print()
    game.running = False
