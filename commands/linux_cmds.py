import random
import re
from commands.registry import register
from ui.console import console
from ui.lang import t


def _require_host(game) -> bool:
    if not game.current_host:
        console.print_error(t("fs.not_connected"))
        return False
    return True


def _wants_help(args) -> bool:
    return bool(args) and args[0] in ("-h", "--help")


def _get_input(game, args, cmd_name: str) -> str | None:
    """Get input: from file arg, or from stdin (pipe). Returns content or None."""
    from commands.filesystem_cmds import _resolve_path

    # Filter out flags and their value arguments (e.g. -n 5)
    file_args = []
    skip_next = False
    for i, a in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if a.startswith("-"):
            # Flags that take a value argument: -n, -c, -f, -d, -s
            if a in ("-n", "-c", "-f", "-d", "-s", "-k", "-t"):
                skip_next = True
            continue
        # Skip pure numbers (likely flag values that weren't caught)
        if a.isdigit():
            continue
        file_args.append(a)

    if file_args:
        filepath = file_args[-1]
        if not filepath.startswith("/"):
            filepath = _resolve_path(game.current_host.cwd, filepath)
        if filepath in game.current_host.files:
            return game.current_host.files[filepath]
        console.print_error(f"{cmd_name}: {filepath}: No such file or directory")
        return None

    # No file arg — try stdin
    if game.stdin:
        return game.stdin

    console.print_error(f"{cmd_name}: missing file operand")
    return None


@register("whoami", "cmd.whoami.help", required_tool="whoami")
def handle_whoami(game, args):
    if _wants_help(args):
        console.print("Usage: whoami")
        console.print("Print the user name associated with the current effective user ID.")
        return
    if not _require_host(game):
        return
    console.print(game.current_host.get_current_user())


@register("pwd", "cmd.pwd.help", required_tool="pwd")
def handle_pwd(game, args):
    if _wants_help(args):
        console.print("Usage: pwd")
        console.print("Print the full filename of the current working directory.")
        return
    if not _require_host(game):
        return
    console.print(game.current_host.cwd)


@register("id", "cmd.id.help", required_tool="id")
def handle_id(game, args):
    if _wants_help(args):
        console.print("Usage: id [OPTIONS] [USER]")
        console.print("  id        print user and group info")
        console.print("  id -u     print only UID")
        console.print("  id -g     print only GID")
        console.print("  id -n     print name instead of number (with -u/-g)")
        console.print("  id -Gn    print all group names")
        return
    if not _require_host(game):
        return
    host = game.current_host
    user = host.get_current_user()
    uid = 0 if user == "root" else 1000
    gid = uid
    if user != "root":
        for i, u in enumerate(host.users):
            if u.get("name") == user:
                uid = 1000 + i
                gid = uid
                break
    groups_str = f"{uid}({user}),27(sudo),33(www-data)" if user != "root" else "0(root)"

    _fl = "".join(a[1:] for a in args if a.startswith("-"))
    name_mode = "n" in _fl
    if "u" in _fl:
        console.print(user if name_mode else str(uid))
    elif "g" in _fl:
        console.print(user if name_mode else str(gid))
    elif "G" in _fl:
        if name_mode:
            console.print(f"{user} sudo www-data" if user != "root" else "root")
        else:
            console.print(f"{uid} 27 33" if user != "root" else "0")
    else:
        console.print(f"uid={uid}({user}) gid={gid}({user}) groups={groups_str}")


@register("uname", "cmd.uname.help", required_tool="uname")
def handle_uname(game, args):
    if _wants_help(args):
        console.print("Usage: uname [OPTION]...")
        console.print("Print certain system information.\n")
        console.print("  -a   print all information")
        console.print("  -r   print the kernel release")
        console.print("  -n   print the network node hostname")
        console.print("  -s   print the kernel name (default)")
        return
    if not _require_host(game):
        return
    host = game.current_host
    kernel = "5.4.0-42-generic" if "20" in host.os else "5.15.0-91-generic"
    # Parse combined flags
    flags = set()
    for a in args:
        if a.startswith("-") and a != "--help":
            for c in a[1:]:
                flags.add(c)

    if "a" in flags:
        console.print(f"Linux {host.hostname} {kernel} #46-Ubuntu SMP x86_64 GNU/Linux")
    elif not flags:
        console.print("Linux")
    else:
        parts = []
        if "s" in flags:
            parts.append("Linux")
        if "n" in flags:
            parts.append(host.hostname)
        if "r" in flags:
            parts.append(kernel)
        if "v" in flags:
            parts.append("#46-Ubuntu SMP")
        if "m" in flags:
            parts.append("x86_64")
        if "p" in flags:
            parts.append("x86_64")
        if "o" in flags:
            parts.append("GNU/Linux")
        console.print(" ".join(parts) if parts else "Linux")


@register("hostname", "cmd.hostname.help", required_tool="hostname")
def handle_hostname(game, args):
    if _wants_help(args):
        console.print("Usage: hostname [OPTION]")
        console.print("Show or set the system's host name.\n")
        console.print("  -I   display all network addresses of the host")
        console.print("  -f   display the FQDN")
        return
    if not _require_host(game):
        return
    if args and "-I" in args:
        console.print(game.current_host.ip)
    else:
        console.print(game.current_host.hostname)


@register("ifconfig", "cmd.ifconfig.help", required_tool="ifconfig")
def handle_ifconfig(game, args):
    if _wants_help(args):
        console.print("Usage: ifconfig [INTERFACE]")
        console.print("Configure or display network interface parameters.\n")
        console.print("  ifconfig          display all active interfaces")
        console.print("  ifconfig eth0     display info for eth0")
        return
    if not _require_host(game):
        return
    host = game.current_host
    mac = ":".join(f"{random.randint(0,255):02x}" for _ in range(6))
    output = f"""eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet {host.ip}  netmask 255.255.255.0  broadcast {host.ip.rsplit('.', 1)[0]}.255
        inet6 fe80::1  prefixlen 64  scopeid 0x20<link>
        ether {mac}  txqueuelen 1000  (Ethernet)
        RX packets {random.randint(10000, 999999)}  bytes {random.randint(1000000, 999999999)}
        TX packets {random.randint(10000, 999999)}  bytes {random.randint(1000000, 999999999)}

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1  prefixlen 128  scopeid 0x10<host>
        loop  txqueuelen 1000  (Local Loopback)"""
    # Show VPN tunnel if on attacker machine and target network exists
    if game.is_on_localhost() and game.current_network:
        subnet_base = game.current_network.subnet.split("/")[0].rsplit(".", 1)[0]
        mac2 = ":".join(f"{random.randint(0,255):02x}" for _ in range(6))
        output += f"""

tun0: flags=4305<UP,POINTOPOINT,RUNNING,NOARP,MULTICAST>  mtu 1500
        inet {subnet_base}.254  netmask 255.255.255.0
        ether {mac2}  txqueuelen 500  (UNSPEC)
        RX packets {random.randint(1000, 99999)}  bytes {random.randint(100000, 99999999)}
        TX packets {random.randint(1000, 99999)}  bytes {random.randint(100000, 99999999)}"""
    console.print(output)


@register("ip", "cmd.ip.help", required_tool="ip")
def handle_ip(game, args):
    if not args or _wants_help(args):
        console.print("Usage: ip [ OPTIONS ] OBJECT { COMMAND }\n")
        console.print("OBJECT := { addr | route | link | neigh | rule }\n")
        console.print("  ip addr        show addresses")
        console.print("  ip a           (same as ip addr)")
        console.print("  ip route       show routing table")
        console.print("  ip r           (same as ip route)")
        console.print("  ip link        show link-layer info")
        return
    if not _require_host(game):
        return
    host = game.current_host
    if args[0] in ("a", "addr", "address"):
        mac = ":".join(f"{random.randint(0,255):02x}" for _ in range(6))
        output = f"""1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether {mac} brd ff:ff:ff:ff:ff:ff
    inet {host.ip}/24 brd {host.ip.rsplit('.', 1)[0]}.255 scope global eth0
       valid_lft forever preferred_lft forever"""
        if game.is_on_localhost() and game.current_network:
            subnet_base = game.current_network.subnet.split("/")[0].rsplit(".", 1)[0]
            output += f"""
3: tun0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UNKNOWN group default qlen 500
    inet {subnet_base}.254/24 scope global tun0
       valid_lft forever preferred_lft forever"""
        console.print(output)
    elif args[0] in ("r", "route"):
        gw = host.ip.rsplit(".", 1)[0] + ".1"
        output = f"""default via {gw} dev eth0 proto static
{host.ip.rsplit('.', 1)[0]}.0/24 dev eth0 proto kernel scope link src {host.ip}"""
        if game.is_on_localhost() and game.current_network:
            subnet = game.current_network.subnet
            subnet_base = subnet.split("/")[0].rsplit(".", 1)[0]
            output += f"\n{subnet} dev tun0 proto kernel scope link src {subnet_base}.254"
        console.print(output)
    elif args[0] in ("l", "link"):
        mac = ":".join(f"{random.randint(0,255):02x}" for _ in range(6))
        console.print(f"""1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000
    link/ether {mac} brd ff:ff:ff:ff:ff:ff""")
    elif args[0] in ("n", "neigh"):
        gw = host.ip.rsplit(".", 1)[0] + ".1"
        mac = ":".join(f"{random.randint(0,255):02x}" for _ in range(6))
        console.print(f"{gw} dev eth0 lladdr {mac} REACHABLE")
    else:
        console.print(f"Command \"{args[0]}\" is unknown, try \"ip help\".")


@register("ps", "cmd.ps.help", required_tool="ps")
def handle_ps(game, args):
    if _wants_help(args):
        console.print("Usage: ps [OPTIONS]\n")
        console.print("  ps             show your processes")
        console.print("  ps aux         show all processes (detailed)")
        console.print("  ps -ef         show all processes (full format)")
        return
    if not _require_host(game):
        return
    host = game.current_host
    user = host.get_current_user()

    processes = [
        ("root", "1", "0.0", "0.1", "init", "/sbin/init"),
        ("root", "2", "0.0", "0.0", "kthreadd", "[kthreadd]"),
        ("root", str(random.randint(200, 400)), "0.0", "0.1", "systemd-journal", "/lib/systemd/systemd-journald"),
        ("root", str(random.randint(400, 600)), "0.0", "0.0", "systemd-udevd", "/lib/systemd/systemd-udevd"),
        ("syslog", str(random.randint(600, 700)), "0.0", "0.1", "rsyslogd", "/usr/sbin/rsyslogd -n"),
        ("root", str(random.randint(700, 800)), "0.0", "0.2", "cron", "/usr/sbin/cron -f"),
    ]

    for svc in host.services:
        pid = str(random.randint(800, 2000))
        if svc.name == "ssh":
            processes.append(("root", pid, "0.0", "0.1", "sshd", "/usr/sbin/sshd -D"))
        elif svc.name in ("http", "apache"):
            processes.append(("root", pid, "0.1", "0.5", "apache2", "/usr/sbin/apache2 -k start"))
            processes.append(("www-data", str(int(pid)+1), "0.0", "0.3", "apache2", "/usr/sbin/apache2 -k start"))
        elif svc.name == "mysql":
            processes.append(("mysql", pid, "0.5", "5.2", "mysqld", "/usr/sbin/mysqld"))
        elif svc.name == "nginx":
            processes.append(("root", pid, "0.0", "0.1", "nginx", "nginx: master process"))
            processes.append(("www-data", str(int(pid)+1), "0.0", "0.2", "nginx", "nginx: worker process"))

    processes.append((user, str(random.randint(2000, 3000)), "0.0", "0.1", "bash", "-bash"))
    processes.append((user, str(random.randint(3000, 4000)), "0.0", "0.0", "ps", "ps aux"))

    show_all = args and ("aux" in args or "-ef" in args or "-e" in args or "a" in args)

    console.print(f"{'USER':10s} {'PID':>6s} {'%CPU':>5s} {'%MEM':>5s} {'COMMAND'}")
    for proc in processes:
        p_user, pid, cpu, mem, name, cmd = proc
        if show_all or p_user == user or p_user == "root":
            console.print(f"{p_user:10s} {pid:>6s} {cpu:>5s} {mem:>5s} {cmd}")


@register("env", "cmd.env.help", required_tool="env")
def handle_env(game, args):
    if _wants_help(args):
        console.print("Usage: env")
        console.print("Print the current environment variables.")
        return
    if not _require_host(game):
        return
    for key, val in game.current_host.env.items():
        console.print(f"{key}={val}")


@register("echo", "cmd.echo.help", required_tool="echo")
def handle_echo(game, args):
    if _wants_help(args):
        console.print("Usage: echo [OPTIONS] [STRING]...\n")
        console.print("  echo text          print text")
        console.print("  echo -n text       no trailing newline")
        console.print('  echo -e "a\\nb"     interpret escape sequences')
        return
    if not _require_host(game):
        return

    no_newline = False
    interpret_escapes = False
    text_args = []
    for a in args:
        if a == "-n":
            no_newline = True
        elif a == "-e":
            interpret_escapes = True
        elif a == "-ne" or a == "-en":
            no_newline = True
            interpret_escapes = True
        else:
            text_args.append(a)

    text = " ".join(text_args)

    if interpret_escapes:
        text = text.replace("\\\\", "\x00")  # protect literal backslash
        text = text.replace("\\n", "\n").replace("\\t", "\t")
        text = text.replace("\\a", "\a").replace("\\r", "\r")
        text = text.replace("\\e", "\033").replace("\\033", "\033")
        text = text.replace("\\b", "\b").replace("\\f", "\f")
        text = text.replace("\\v", "\v").replace("\\0", "\0")
        text = text.replace("\x00", "\\")

    if no_newline:
        console.print(text, end="")
    else:
        console.print(text)


@register("which", "cmd.which.help", required_tool="which")
def handle_which(game, args):
    if _wants_help(args):
        console.print("Usage: which COMMAND")
        console.print("Locate a command binary in PATH.")
        return
    if not _require_host(game):
        return
    if not args:
        console.print("Usage: which COMMAND")
        return
    cmd = args[0]
    host = game.current_host
    for prefix in ["/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]:
        path = f"{prefix}/{cmd}"
        if path in host.files:
            console.print(path)
            return
    console.print(f"{cmd} not found")


@register("date", "cmd.date.help", required_tool="date")
def handle_date(game, args):
    if _wants_help(args):
        console.print("Usage: date [OPTION]... [+FORMAT]")
        console.print("Display the current time and date.\n")
        console.print("  date            show current date/time")
        console.print("  date +%Y        show year")
        console.print("  date +%s        show seconds since epoch")
        console.print("  date +%F        show YYYY-MM-DD")
        return
    from datetime import datetime
    now = datetime.now()
    if args and args[0].startswith("+"):
        fmt = args[0][1:]
        # Convert strftime-style to Python
        py_fmt = fmt.replace("%s", str(int(now.timestamp())))
        # %F and %T are not in Python strftime
        py_fmt = py_fmt.replace("%F", "%Y-%m-%d").replace("%T", "%H:%M:%S")
        try:
            console.print(now.strftime(py_fmt))
        except ValueError:
            console.print(fmt)
    else:
        console.print(now.strftime("%a %b %d %H:%M:%S %Z %Y"))


@register("uptime", "cmd.uptime.help", required_tool="uptime")
def handle_uptime(game, args):
    if _wants_help(args):
        console.print("Usage: uptime")
        console.print("Tell how long the system has been running.")
        return
    if not _require_host(game):
        return
    days = random.randint(1, 365)
    hours = random.randint(0, 23)
    mins = random.randint(0, 59)
    users = len(game.current_host.users) + 1
    load1 = f"0.{random.randint(0,99):02d}"
    load5 = f"0.{random.randint(0,99):02d}"
    load15 = f"0.{random.randint(0,99):02d}"
    console.print(f" 14:32:01 up {days} days, {hours}:{mins:02d},  {users} users,  load average: {load1}, {load5}, {load15}")


@register("free", "cmd.free.help", required_tool="free")
def handle_free(game, args):
    if "--help" in args:
        console.print("Usage: free [OPTIONS]\n")
        console.print("  free            display memory usage")
        console.print("  free -h         human-readable output")
        console.print("  free -m         output in mebibytes")
        return
    if not _require_host(game):
        return
    human = any("h" in a for a in args if a.startswith("-"))
    total = random.randint(4000000, 16000000)
    used = random.randint(total // 4, total * 3 // 4)
    free_mem = total - used
    shared = random.randint(10000, 100000)
    buffers = random.randint(100000, 500000)
    cached = random.randint(500000, 2000000)
    avail = free_mem + cached
    swap_total = total // 2

    def _hfmt(kb):
        if kb > 1000000:
            return f"{kb/1000000:.1f}Gi"
        if kb > 1000:
            return f"{kb/1000:.1f}Mi"
        return f"{kb}Ki"

    if human:
        console.print(f"{'':15s} {'total':>12s} {'used':>12s} {'free':>12s} {'shared':>12s} {'buff/cache':>12s} {'available':>12s}")
        console.print(f"{'Mem:':15s} {_hfmt(total):>12s} {_hfmt(used):>12s} {_hfmt(free_mem):>12s} {_hfmt(shared):>12s} {_hfmt(buffers+cached):>12s} {_hfmt(avail):>12s}")
        console.print(f"{'Swap:':15s} {_hfmt(swap_total):>12s} {'0B':>12s} {_hfmt(swap_total):>12s}")
    else:
        console.print(f"{'':15s} {'total':>12s} {'used':>12s} {'free':>12s} {'shared':>12s} {'buff/cache':>12s} {'available':>12s}")
        console.print(f"{'Mem:':15s} {total:>12d} {used:>12d} {free_mem:>12d} {shared:>12d} {buffers+cached:>12d} {avail:>12d}")
        console.print(f"{'Swap:':15s} {swap_total:>12d} {'0':>12s} {swap_total:>12d}")


@register("df", "cmd.df.help", required_tool="df")
def handle_df(game, args):
    if "--help" in args:
        console.print("Usage: df [OPTIONS] [FILE]...\n")
        console.print("  df              show disk usage for all filesystems")
        console.print("  df -h           human-readable sizes")
        console.print("  df /            show usage for root filesystem")
        return
    if not _require_host(game):
        return
    size = random.randint(15, 100)
    used = random.randint(size // 4, size * 3 // 4)
    avail = size - used
    pct = int(used / size * 100)
    console.print(f"{'Filesystem':20s} {'Size':>6s} {'Used':>6s} {'Avail':>6s} {'Use%':>5s} {'Mounted on'}")
    console.print(f"{'/dev/sda1':20s} {size:>5d}G {used:>5d}G {avail:>5d}G {pct:>4d}% /")
    console.print(f"{'tmpfs':20s} {'4.0':>6s} {'0':>6s} {'4.0':>6s} {'0%':>5s} /tmp")
    console.print(f"{'tmpfs':20s} {'804M':>6s} {'0':>6s} {'804M':>6s} {'0%':>5s} /dev/shm")


@register("mount", "cmd.mount.help", required_tool="mount")
def handle_mount(game, args):
    if _wants_help(args):
        console.print("Usage: mount [-t type] [-o options] device dir\n")
        console.print("  mount           show all mounted filesystems")
        console.print("  mount -t ext4   show only ext4 mounts")
        return
    if not _require_host(game):
        return
    console.print("""/dev/sda1 on / type ext4 (rw,relatime,errors=remount-ro)
sysfs on /sys type sysfs (rw,nosuid,nodev,noexec,relatime)
proc on /proc type proc (rw,nosuid,nodev,noexec,relatime)
udev on /dev type devtmpfs (rw,nosuid,noexec,relatime,size=4039260k,nr_inodes=1009815,mode=755)
devpts on /dev/pts type devpts (rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000)
tmpfs on /run type tmpfs (rw,nosuid,nodev,noexec,relatime,size=812304k,mode=755)
tmpfs on /tmp type tmpfs (rw,relatime)""")


@register("netstat", "cmd.netstat.help", required_tool="netstat")
def handle_netstat(game, args):
    if _wants_help(args):
        console.print("Usage: netstat [OPTIONS]\n")
        console.print("  netstat         show network connections")
        console.print("  netstat -tlnp   show listening TCP ports with PIDs")
        console.print("  netstat -an     show all connections numerically")
        return
    if not _require_host(game):
        return
    host = game.current_host
    console.print(f"{'Proto':6s} {'Recv-Q':>7s} {'Send-Q':>7s} {'Local Address':23s} {'Foreign Address':23s} {'State'}")
    for svc in host.services:
        console.print(f"{'tcp':6s} {'0':>7s} {'0':>7s} {'0.0.0.0:' + str(svc.port):23s} {'0.0.0.0:*':23s} LISTEN")
    console.print(f"{'tcp':6s} {'0':>7s} {'0':>7s} {'127.0.0.1:25':23s} {'0.0.0.0:*':23s} LISTEN")


@register("ss", "cmd.ss.help", required_tool="ss")
def handle_ss(game, args):
    if _wants_help(args):
        console.print("Usage: ss [OPTIONS] [FILTER]\n")
        console.print("  ss              show socket summary")
        console.print("  ss -tlnp        show listening TCP sockets with processes")
        console.print("  ss -an          show all sockets numerically")
        return
    handle_netstat(game, args)


def _parse_line_count(args, default=10):
    """Parse -n N or -N from args, return count. Supports head -3 / tail -n 5."""
    n = default
    for i, a in enumerate(args):
        if a == "-n" and i + 1 < len(args):
            try:
                n = int(args[i + 1])
            except ValueError:
                pass
            break
        if re.match(r'^-(\d+)$', a):
            n = int(a[1:])
            break
    return n


@register("head", "cmd.head.help", required_tool="head")
def handle_head(game, args):
    if _wants_help(args):
        console.print("Usage: head [OPTION]... [FILE]...\n")
        console.print("  head FILE          output the first 10 lines")
        console.print("  head -n 5 FILE     output the first 5 lines")
        console.print("  head -5 FILE       same as -n 5")
        return
    if not _require_host(game):
        return

    n = _parse_line_count(args)

    # Get file args (exclude flags and their values)
    from commands.filesystem_cmds import _resolve_path
    file_args = []
    skip = False
    for a in args:
        if skip: skip = False; continue
        if a in ("-n",): skip = True; continue
        if a.startswith("-"): continue
        if a.isdigit(): continue
        file_args.append(a)

    if len(file_args) > 1:
        # Multi-file: show headers
        host = game.current_host
        for i, f in enumerate(file_args):
            fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
            if fp not in host.files:
                console.print_error(f"head: {f}: No such file or directory")
                continue
            if i > 0:
                console.print("")
            console.print(f"==> {f} <==")
            lines = host.files[fp].splitlines()[:n]
            console.print("\n".join(lines))
    else:
        content = _get_input(game, args, "head")
        if content is None:
            return
        lines = content.splitlines()[:n]
        console.print("\n".join(lines))


@register("tail", "cmd.tail.help", required_tool="tail")
def handle_tail(game, args):
    if _wants_help(args):
        console.print("Usage: tail [OPTION]... [FILE]...\n")
        console.print("  tail FILE          output the last 10 lines")
        console.print("  tail -n 5 FILE     output the last 5 lines")
        console.print("  tail -5 FILE       same as -n 5")
        console.print("  tail -f FILE       output appended data as the file grows")
        return
    if not _require_host(game):
        return

    n = _parse_line_count(args)

    content = _get_input(game, args, "tail")
    if content is None:
        return

    lines = content.splitlines()
    # Remove trailing empty line from final \n (like real tail)
    if lines and lines[-1] == "":
        lines = lines[:-1]
    lines = lines[-n:]
    console.print("\n".join(lines))


def _grep_content(content: str, pattern: str, case_i: bool, invert: bool,
                   only_match: bool, use_regex: bool = False) -> list[tuple[int, str]]:
    """Return list of (lineno, line) matching pattern."""
    import re as _re
    results = []
    flags = _re.IGNORECASE if case_i else 0

    for i, line in enumerate(content.split("\n"), 1):
        if use_regex:
            try:
                m = _re.search(pattern, line, flags)
                matched = m is not None
            except _re.error:
                matched = False
                m = None
        else:
            cl = line.lower() if case_i else line
            cp = pattern.lower() if case_i else pattern
            matched = cp in cl
            m = None

        if invert:
            matched = not matched

        if matched:
            if only_match and not invert:
                if use_regex and m:
                    results.append((i, m.group()))
                elif not use_regex:
                    cp2 = pattern.lower() if case_i else pattern
                    cl2 = line.lower() if case_i else line
                    idx = cl2.find(cp2)
                    results.append((i, line[idx:idx + len(pattern)]))
            else:
                results.append((i, line))
    return results


@register("grep", "cmd.grep.help", required_tool="grep")
def handle_grep(game, args):
    if _wants_help(args):
        console.print("Usage: grep [OPTIONS] PATTERN [FILE]...\n")
        console.print("  grep root /etc/passwd       find lines with 'root'")
        console.print("  grep -i password file.txt   case-insensitive search")
        console.print("  grep -v pattern file        invert match")
        console.print("  grep -n pattern file        show line numbers")
        console.print("  grep -c pattern file        count matching lines")
        console.print("  cmd | grep pattern          read from stdin")
        return
    if not _require_host(game):
        return
    from commands.filesystem_cmds import _resolve_path

    # Parse flags, handling -A N, -B N, -C N, -A3, -B2 for context
    flags = []
    non_flags = []
    after_ctx = before_ctx = 0
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-A", "-B", "-C") and i + 1 < len(args):
            try:
                val = int(args[i + 1])
                if a == "-A": after_ctx = val
                elif a == "-B": before_ctx = val
                elif a == "-C": before_ctx = after_ctx = val
            except ValueError: pass
            i += 2
        elif re.match(r'^-A(\d+)$', a):
            after_ctx = int(a[2:])
            i += 1
        elif re.match(r'^-B(\d+)$', a):
            before_ctx = int(a[2:])
            i += 1
        elif re.match(r'^-C(\d+)$', a):
            before_ctx = after_ctx = int(a[2:])
            i += 1
        elif a.startswith("-") and len(a) > 1 and a[1:].isdigit():
            before_ctx = after_ctx = int(a[1:])
            i += 1
        elif a.startswith("-"):
            flags.append(a)
            i += 1
        else:
            non_flags.append(a)
            i += 1

    if not non_flags:
        console.print_error("grep: missing pattern")
        return 1

    pattern = non_flags[0]
    file_args = non_flags[1:]

    _allflags = "".join(f[1:] for f in flags)
    case_insensitive = "i" in _allflags
    count_only = "c" in _allflags
    invert = "v" in _allflags
    show_numbers = "n" in _allflags
    recursive = "r" in _allflags or "R" in _allflags
    only_match = "o" in _allflags
    files_only = "l" in _allflags
    use_regex = "E" in _allflags or "P" in _allflags
    whole_word = "w" in _allflags
    if whole_word and not use_regex:
        pattern = r'\b' + re.escape(pattern) + r'\b'
        use_regex = True

    host = game.current_host

    # Recursive mode: search all files under a directory
    if recursive and file_args:
        search_dir = file_args[0]
        if not search_dir.startswith("/"):
            search_dir = _resolve_path(host.cwd, search_dir)
        # If target is a file (not a directory), fall through to normal grep
        if search_dir in host.files:
            recursive = False
            file_args = [search_dir]
        else:
            pass  # continue with recursive search below

    if recursive and file_args:
        search_dir = file_args[0]
        if not search_dir.startswith("/"):
            search_dir = _resolve_path(host.cwd, search_dir)
        prefix = search_dir.rstrip("/") + "/" if search_dir != "/" else "/"
        target_files = {fp: host.files[fp] for fp in host.files
                        if fp.startswith(prefix) and not host.files[fp].startswith("[ELF ")
                        and not host.files[fp].startswith("[binary")}
        total_count = 0
        for fp, content in sorted(target_files.items()):
            fc = _grep_content(content, pattern, case_insensitive, invert, only_match, use_regex)
            if fc:
                total_count += len(fc)
                if files_only:
                    console.print(fp)
                elif count_only:
                    console.print(f"{fp}:{len(fc)}")
                else:
                    for ln, line in fc:
                        pref = f"{fp}:" + (f"{ln}:" if show_numbers else "")
                        console.print(f"{pref}{line}")
        return 0 if total_count > 0 else 1

    # Get content from file or stdin
    if file_args:
        filepath = file_args[0]
        if not filepath.startswith("/"):
            filepath = _resolve_path(host.cwd, filepath)
        if filepath not in host.files:
            console.print_error(f"grep: {filepath}: No such file or directory")
            return 1
        content = host.files[filepath]
    elif game.stdin:
        content = game.stdin
    else:
        console.print_error("grep: missing file operand")
        return 1

    matches = _grep_content(content, pattern, case_insensitive, invert, only_match, use_regex)
    count = len(matches)

    if not count_only:
        if (before_ctx > 0 or after_ctx > 0) and not only_match:
            # Context mode: show surrounding lines
            all_lines = content.split("\n")
            match_linenos = {ln for ln, _ in matches}
            shown = set()
            prev_shown = -2
            for ln, line in matches:
                for ctx_ln in range(max(1, ln - before_ctx), min(len(all_lines) + 1, ln + after_ctx + 1)):
                    if ctx_ln in shown:
                        continue
                    if prev_shown >= 0 and ctx_ln > prev_shown + 1:
                        console.print("--")
                    shown.add(ctx_ln)
                    prev_shown = ctx_ln
                    ctx_line = all_lines[ctx_ln - 1] if ctx_ln <= len(all_lines) else ""
                    sep = ":" if ctx_ln in match_linenos else "-"
                    if show_numbers:
                        console.print(f"{ctx_ln}{sep}{ctx_line}")
                    else:
                        console.print(f"{ctx_line}")
        else:
            for ln, line in matches:
                prefix = f"{ln}:" if show_numbers else ""
                if not console.capturing and not invert:
                    highlighted = line.replace(pattern, f"[bold red]{pattern}[/bold red]")
                    console.print(f"{prefix}{highlighted}")
                else:
                    console.print(f"{prefix}{line}")

    if count_only:
        console.print(str(count))

    return 0 if count > 0 else 1


@register("wc", "cmd.wc.help", required_tool="wc")
def handle_wc(game, args):
    if _wants_help(args):
        console.print("Usage: wc [OPTION]... [FILE]...\n")
        console.print("  wc FILE        print line, word, and byte counts")
        console.print("  wc -l FILE     print only line count")
        console.print("  wc -w FILE     print only word count")
        return
    if not _require_host(game):
        return
    from commands.filesystem_cmds import _resolve_path

    flags = [a for a in args if a.startswith("-")]
    _fl = "".join(f[1:] for f in flags)
    has_l = "l" in _fl
    has_w = "w" in _fl
    has_c = "c" in _fl or "m" in _fl
    show_all = not has_l and not has_w and not has_c

    file_args = [a for a in args if not a.startswith("-")]
    host = game.current_host

    def _wc_print(l, w, c, name):
        parts = []
        if show_all:
            console.print(f"{l:>8d} {w:>8d} {c:>8d} {name}".rstrip())
        else:
            if has_l: parts.append(f"{l:>8d}")
            if has_w: parts.append(f"{w:>8d}")
            if has_c: parts.append(f"{c:>8d}")
            console.print(f"{''.join(parts)} {name}".rstrip())

    if not file_args:
        # stdin
        if game.stdin:
            content = game.stdin
        else:
            console.print_error("wc: missing file operand")
            return 1
        _wc_print(content.count("\n"), len(content.split()), len(content), "")
        return

    total_l = total_w = total_c = 0
    for f in file_args:
        fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
        if fp not in host.files:
            console.print_error(f"wc: {f}: No such file or directory")
            continue
        content = host.files[fp]
        l = content.count("\n")
        w = len(content.split())
        c = len(content)
        total_l += l; total_w += w; total_c += c
        _wc_print(l, w, c, f.split("/")[-1])

    if len(file_args) > 1:
        _wc_print(total_l, total_w, total_c, "total")
    return 0


@register("sudo", "cmd.sudo.help", required_tool="sudo")
def handle_sudo(game, args):
    if _wants_help(args):
        console.print("Usage: sudo [OPTION]... COMMAND\n")
        console.print("  sudo command        run command as root")
        console.print("  sudo su             switch to root shell")
        console.print("  sudo -l             list allowed commands")
        return
    if not _require_host(game):
        return
    if not args:
        console.print("usage: sudo [-u user] command")
        return

    host = game.current_host
    if host.access_level == "root":
        from commands.registry import dispatch
        dispatch(game, " ".join(args))
        return

    if args[0] == "-l":
        user = host.get_current_user()
        console.print(f"User {user} may run the following commands on {host.hostname}:")
        console.print(f"    (ALL : ALL) ALL")
        return

    console.print(f"[sudo] password for {host.get_current_user()}: [dim]********[/dim]")

    old_level = host.access_level
    host.access_level = "root"
    old_env_user = host.env.get("USER", "")
    host.env["USER"] = "root"

    from commands.registry import dispatch
    dispatch(game, " ".join(args))

    if args[0] != "su":
        host.access_level = old_level
        host.env["USER"] = old_env_user


@register("su", "cmd.su.help", required_tool="su")
def handle_su(game, args):
    if _wants_help(args):
        console.print("Usage: su [OPTIONS] [USER]\n")
        console.print("  su              switch to root (requires password)")
        console.print("  su -            switch to root with login shell")
        console.print("  su username     switch to another user")
        return
    if not _require_host(game):
        return
    host = game.current_host

    target_user = "root"
    if args and args[0] != "-":
        target_user = args[0]
    elif len(args) > 1:
        target_user = args[1]

    if target_user == "root":
        if host.access_level == "root":
            console.print_info("Already root.")
            return
        root_cred = game.player.has_credential_for(host.ip, "root")
        if root_cred:
            host.access_level = "root"
            host.env["USER"] = "root"
            host.env["HOME"] = "/root"
            host.cwd = "/root"
            console.print_info("root access obtained.")
            game.check_objective("compromise_host", ip=host.ip)
        else:
            console.print_error("su: Authentication failure")
    else:
        console.print(f"su: user {target_user}: switching not supported in this simulation")


@register("chmod", "cmd.chmod.help", required_tool="chmod")
def handle_chmod(game, args):
    if _wants_help(args):
        console.print("Usage: chmod [OPTION]... MODE FILE...\n")
        console.print("  chmod 755 file    set rwxr-xr-x")
        console.print("  chmod +x file     add execute permission")
        console.print("  chmod u+w file    add write for owner")
        return
    if not _require_host(game):
        return
    if len(args) < 2:
        console.print_error("chmod: missing operand")
        return

    from commands.filesystem_cmds import _resolve_path
    host = game.current_host
    mode_str = args[0]
    files = args[1:]
    recursive = "-R" in args
    if recursive:
        files = [a for a in files if a != "-R"]

    for f in files:
        fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
        if fp not in host.files and not any(x.startswith(fp + "/") for x in host.files):
            console.print_error(f"chmod: cannot access '{f}': No such file or directory")
            continue

        new_perms = _apply_chmod(mode_str, host.file_meta.get(fp, {}).get("perms", "-rw-r--r--"))
        if fp in host.file_meta:
            host.file_meta[fp]["perms"] = new_perms
        else:
            host.file_meta[fp] = {"perms": new_perms, "owner": "root", "group": "root", "mtime": "Nov 15 14:32"}

        if recursive:
            prefix = fp.rstrip("/") + "/"
            for ff in list(host.files.keys()):
                if ff.startswith(prefix) and ff in host.file_meta:
                    host.file_meta[ff]["perms"] = _apply_chmod(mode_str, host.file_meta[ff].get("perms", "-rw-r--r--"))


def _apply_chmod(mode_str: str, current: str) -> str:
    """Apply chmod mode (numeric like 755 or symbolic like u+x) to permission string."""
    if mode_str.isdigit() and len(mode_str) in (3, 4):
        # Numeric: 755 → rwxr-xr-x, 4755 → rwsr-xr-x
        if len(mode_str) == 4:
            special = int(mode_str[0])
            bits = [int(c) for c in mode_str[1:]]
        else:
            special = 0
            bits = [int(c) for c in mode_str]
        result = "-"
        for i, b in enumerate(bits):
            result += "r" if b & 4 else "-"
            result += "w" if b & 2 else "-"
            if i == 0 and special & 4:  # SUID
                result += "s" if b & 1 else "S"
            elif i == 1 and special & 2:  # SGID
                result += "s" if b & 1 else "S"
            elif i == 2 and special & 1:  # sticky
                result += "t" if b & 1 else "T"
            else:
                result += "x" if b & 1 else "-"
        return result

    # Symbolic: u+x, g-w, o=r, a+x, +x, u+x,g-w
    perms = list(current)
    who_map = {"u": [1, 2, 3], "g": [4, 5, 6], "o": [7, 8, 9], "a": [1, 2, 3, 4, 5, 6, 7, 8, 9]}

    import re as re_mod
    # Support comma-separated specs: u+x,g-w,o=r
    for spec in mode_str.split(","):
        m = re_mod.match(r'([ugoa]*)([+\-=])([rwxXst]+)', spec.strip())
        if not m:
            continue

        who = m.group(1) or "a"
        op = m.group(2)
        what = m.group(3)

        positions = set()
        for w in who:
            if w in who_map:
                positions.update(who_map[w])

        for pos in positions:
            for p in what:
                if p in ("X", "s", "t"):
                    continue  # Skip special bits for now
                p_offset = {"r": 0, "w": 1, "x": 2}.get(p)
                if p_offset is None:
                    continue
                group_start = ((pos - 1) // 3) * 3 + 1
                actual_pos = group_start + p_offset
                if actual_pos < len(perms):
                    if op == "+":
                        perms[actual_pos] = p
                    elif op == "-":
                        perms[actual_pos] = "-"
                    elif op == "=":
                        perms[actual_pos] = p

    return "".join(perms)


@register("man", "cmd.man.help", required_tool="man")
def handle_man(game, args):
    if not args or _wants_help(args):
        console.print("Usage: man [SECTION] PAGE...\n")
        console.print("  man ls          show manual page for ls")
        console.print("  man 5 passwd    show passwd(5) file format manual")
        console.print("  man -k keyword  search manual pages")
        return
    cmd = args[0]
    console.print(f"[bold]{cmd.upper()}(1)[/bold]{'':40s}User Commands\n")
    console.print(f"[bold]NAME[/bold]")
    console.print(f"       {cmd} - use 'help {cmd}' for game help\n")
    console.print(f"[bold]DESCRIPTION[/bold]")
    console.print(f"       This is a simulated man page. Use 'help {cmd}' for in-game help.\n")


@register("history", "cmd.history.help", required_tool="history")
def handle_history(game, args):
    if _wants_help(args):
        console.print("Usage: history [N]\n")
        console.print("  history        show all command history")
        console.print("  history 5      show last 5 commands")
        console.print("  history -c     clear history")
        return
    from ui.prompt import get_history_list
    hist = get_history_list()

    if args and args[0] == "-c":
        hist.clear()
        console.print("[dim]history cleared[/dim]")
        return

    n = len(hist)
    if args and args[0].isdigit():
        n = int(args[0])

    start = max(0, len(hist) - n)
    for i, cmd in enumerate(hist[start:], start + 1):
        console.print(f" {i:>4d}  {cmd}")
