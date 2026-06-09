import random
from commands.registry import register
from commands.filesystem_cmds import _resolve_path
from ui.console import console
from ui.lang import t
from ui.animations import fake_progress, scan_animation
from ui.banners import show_access_denied
from engine.filesystem import generate_motd


def _resolve_host(game, name: str) -> str:
    """
    Resolve a hostname to IP via /etc/hosts on the current host.
    Returns the original string if it's already an IP or can't be resolved.
    """
    # Already an IP?
    parts = name.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return name
    if name == "localhost":
        return "127.0.0.1"

    # Look up in /etc/hosts of the current host
    host = game.current_host
    if host and "/etc/hosts" in host.files:
        for line in host.files["/etc/hosts"].split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) >= 2 and name in fields[1:]:
                return fields[0]

    # Try matching by hostname in any known network
    for net in game.networks.values():
        for h in net.hosts:
            if h.hostname == name:
                return h.ip

    return name  # return as-is, will fail later


def _normalize_subnet(target: str) -> str | None:
    """Normalize '192.168.1.9/24' → '192.168.1.0/24'. Returns None if invalid."""
    if "/" not in target:
        return None
    ip_part, mask = target.rsplit("/", 1)
    try:
        mask_int = int(mask)
    except ValueError:
        return None
    octets = ip_part.split(".")
    if len(octets) != 4:
        return None
    # Zero out host bits for /24
    if mask_int == 24:
        octets[3] = "0"
    elif mask_int == 16:
        octets[2] = "0"
        octets[3] = "0"
    return ".".join(octets) + f"/{mask_int}"


def _find_network_for_subnet(game, subnet: str):
    """Find a network matching the normalized subnet."""
    for net in game.networks.values():
        if _normalize_subnet(net.subnet) == subnet:
            return net
    return None


def _find_host_anywhere(game, ip: str):
    """Find a host in any loaded network, or localhost."""
    if game.localhost and game.localhost.ip == ip:
        return game.localhost
    for net in game.networks.values():
        host = net.get_host(ip)
        if host:
            return host
    return None


def _is_self(game, target: str) -> bool:
    """Check if the target (IP or hostname) is one of our own addresses."""
    ip = _resolve_host(game, target)
    if game.localhost:
        if ip == game.localhost.ip or ip.startswith("127."):
            return True
        if ip == game.localhost.hostname:
            return True
        # Check if resolved to our tun0 VPN address
        if game.current_network:
            subnet_base = game.current_network.subnet.split("/")[0].rsplit(".", 1)[0]
            if ip == f"{subnet_base}.254":
                return True
    return False


@register("nmap", "cmd.nmap.help", required_tool="nmap")
def handle_nmap(game, args):
    if not args or args[0] in ("-h", "--help"):
        console.print("Usage: nmap [OPTIONS] TARGET\n")
        console.print("  nmap 192.168.1.0/24       scan subnet")
        console.print("  nmap 192.168.1.10         scan single host")
        console.print("  nmap -sV host             version detection")
        console.print("  nmap -sC host             default scripts")
        console.print("  nmap -O host              OS detection")
        console.print("  nmap -A host              aggressive (sV+sC+O+traceroute)")
        console.print("  nmap -p 1-1000 host       port range")
        console.print("  nmap -Pn host             skip ping, assume up")
        console.print("  nmap -oN file host        save output to file")
        return

    # Find target: last non-flag argument (or the arg after -oN is a file, skip it)
    skip_next = False
    target = None
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a in ("-oN", "-oX", "-oG", "-oA", "-p", "--script"):
            skip_next = True
            continue
        if a.startswith("-"):
            continue
        target = a

    if not target:
        console.print_error(t("nmap.usage"))
        return

    # Subnet scan
    if "/" in target:
        normalized = _normalize_subnet(target)
        if not normalized:
            console.print_error(t("nmap.host_not_found", target=target))
            return

        network = _find_network_for_subnet(game, normalized)

        # Scanning own local subnet
        if game.localhost and normalized == _normalize_subnet(game.localhost.ip + "/24"):
            console.print_info(t("nmap.starting", target=normalized))
            scan_animation([game.localhost.ip], seconds=1.5)
            console.print_table(
                t("nmap.results_for", target=normalized),
                [t("nmap.header_host"), t("nmap.header_status"), t("nmap.header_hostname")],
                [[game.localhost.ip, "[green]up[/green]", game.localhost.hostname]],
                styles=["cyan", "green", "white"],
            )
            console.print(f"[dim]{t('nmap.done', count=1)}[/dim]")
            return

        if not network:
            console.print_info(t("nmap.starting", target=normalized))
            fake_progress(t("anim.scanning", target=normalized), seconds=2.0)
            console.print(f"[dim]{t('nmap.done', count=0)}[/dim]")
            return

        console.print_info(t("nmap.starting", target=normalized))
        all_ips = network.get_all_ips()
        scan_animation(all_ips, seconds=2.5)

        for ip in all_ips:
            network.discover_host(ip)

        console.print_table(
            t("nmap.results_for", target=normalized),
            [t("nmap.header_host"), t("nmap.header_status"), t("nmap.header_hostname")],
            [[ip, "[green]up[/green]", (network.get_host(ip).hostname if network.get_host(ip) else "unknown")]
             for ip in all_ips],
            styles=["cyan", "green", "white"],
        )
        console.print(f"[dim]{t('nmap.done', count=len(all_ips))}[/dim]")
        game.check_objective("discover_hosts", count=len(network.discovered_hosts))
        return

    # Single host scan — resolve hostname
    target = _resolve_host(game, target)

    if _is_self(game, target):
        # Scanning ourselves
        console.print_info(t("nmap.starting", target=target))
        fake_progress(t("anim.scanning", target=target), seconds=1.5)
        console.print_table(
            t("nmap.results_for", target=f"{target} ({game.localhost.hostname})"),
            [t("nmap.header_port"), t("nmap.header_state"), t("nmap.header_service"), t("nmap.header_version")],
            [],
            styles=["cyan", "green", "magenta", "white"],
        )
        console.print(f"[dim]All 1000 scanned ports are closed[/dim]")
        return

    host = _find_host_anywhere(game, target)
    if not host:
        console.print_error(t("nmap.host_not_found", target=target))
        return

    for net in game.networks.values():
        if net.get_host(target):
            net.discover_host(target)
            break

    # Parse nmap flags
    flags_str = " ".join(a for a in args if a.startswith("-"))
    version_detect = "-sV" in flags_str or "-A" in flags_str
    script_scan = "-sC" in flags_str or "-A" in flags_str
    os_detect = "-O" in flags_str or "-A" in flags_str
    aggressive = "-A" in flags_str
    output_file = None
    if "-oN" in args:
        idx = args.index("-oN")
        if idx + 1 < len(args):
            output_file = args[idx + 1]

    scan_time = 3.0 if (version_detect or script_scan) else 2.0

    console.print_info(t("nmap.starting", target=target))
    fake_progress(t("anim.scanning", target=target), seconds=scan_time)

    rows = []
    for svc in host.services:
        port_str = f"{svc.port}/tcp"
        state = "[port.open]open[/port.open]"
        service_str = f"[service]{svc.name}[/service]"
        version_str = svc.version if version_detect else ""
        if svc.vulnerable:
            version_str += f" [vuln]({t('nmap.potentially_vulnerable')})[/vuln]"
        rows.append([port_str, state, service_str, version_str])

    headers = [t("nmap.header_port"), t("nmap.header_state"), t("nmap.header_service")]
    styles = ["cyan", "green", "magenta"]
    if version_detect:
        headers.append(t("nmap.header_version"))
        styles.append("white")

    console.print_table(
        t("nmap.results_for", target=f"{target} ({host.hostname})"),
        headers, rows, styles=styles,
    )

    # OS detection
    if os_detect:
        console.print(f"[dim]OS details: {host.os}[/dim]")
        console.print(f"[dim]Network Distance: {random.randint(1, 5)} hops[/dim]")

    # Script scan results
    if script_scan:
        for svc in host.services:
            if svc.vulnerable:
                console.print(f"\n[bold yellow]| {svc.name}-{svc.port}:[/bold yellow]")
                console.print(f"[yellow]|   VULNERABLE:[/yellow]")
                console.print(f"[yellow]|   {svc.exploit_name}[/yellow]")
                console.print(f"[yellow]|     State: VULNERABLE[/yellow]")
                console.print(f"[yellow]|     Risk factor: High[/yellow]")
                console.print(f"[yellow]|     References: CVE-2024-{random.randint(1000,9999)}[/yellow]")

    if aggressive:
        console.print(f"\n[dim]TRACEROUTE[/dim]")
        console.print(f"[dim]HOP RTT     ADDRESS[/dim]")
        gw = target.rsplit(".", 1)[0] + ".1"
        console.print(f"[dim]1   1.23 ms {gw}[/dim]")
        console.print(f"[dim]2   5.67 ms {target}[/dim]")

    console.print(f"\n[dim]OS: {host.os} | Firewall: {'Level ' + str(host.firewall_level) if host.firewall_level else 'None'}[/dim]")

    # Save to file if -oN
    if output_file and game.current_host:
        from commands.file_edit_cmds import _track_file
        fp = output_file if output_file.startswith("/") else _resolve_path(game.current_host.cwd, output_file)
        output_text = f"# Nmap scan report for {target} ({host.hostname})\n"
        for svc in host.services:
            output_text += f"{svc.port}/tcp open {svc.name} {svc.version}\n"
        if os_detect:
            output_text += f"OS details: {host.os}\n"
        _track_file(game.current_host, fp, output_text)
        console.print_info(f"Output saved to {output_file}")


@register("ping", "cmd.ping.help", required_tool="ping")
def handle_ping(game, args):
    if not args or args[0] in ("-h", "--help"):
        console.print("Usage: ping [OPTIONS] HOST\n")
        console.print("  ping host           send ICMP echo")
        console.print("  ping -c 4 host      send 4 pings")
        return

    import time as _time
    import random as _rnd

    count = 0
    for i, a in enumerate(args):
        if a == "-c" and i + 1 < len(args):
            try:
                count = int(args[i + 1])
            except ValueError:
                pass

    target = args[-1]
    ip = _resolve_host(game, target)
    display = f"{target} ({ip})" if ip != target else target
    is_up = _is_self(game, ip) or _find_host_anywhere(game, ip) is not None

    if count > 0:
        console.print(f"PING {target} ({ip}) 56(84) bytes of data.")
        sent, received = 0, 0
        for seq in range(1, min(count, 20) + 1):
            if is_up:
                ms = _rnd.uniform(0.5, 25.0)
                console.print(f"64 bytes from {ip}: icmp_seq={seq} ttl=64 time={ms:.1f} ms")
                received += 1
            sent += 1
            if seq < count:
                _time.sleep(0.3)
        loss = int((sent - received) / sent * 100) if sent else 100
        console.print(f"\n--- {target} ping statistics ---")
        console.print(f"{sent} packets transmitted, {received} received, {loss}% packet loss")
        if received:
            console.print(f"rtt min/avg/max = {_rnd.uniform(0.5,5):.3f}/{_rnd.uniform(5,15):.3f}/{_rnd.uniform(15,30):.3f} ms")
    else:
        if is_up:
            console.print(f"[green]{t('ping.up', target=display)}[/green]")
        else:
            console.print(f"[red]{t('ping.down', target=display)}[/red]")


@register("ssh", "cmd.ssh.help", required_tool="ssh")
def handle_ssh(game, args):
    if not args or args[0] in ("-h", "--help"):
        console.print("Usage: ssh [OPTIONS] USER@HOST\n")
        console.print("  ssh user@192.168.1.10       connect to host")
        console.print("  ssh -p 2222 user@host       connect on custom port")
        return

    target = args[-1]  # support flags before user@host
    if "@" not in target:
        console.print_error(t("ssh.usage"))
        return

    username, raw_host = target.split("@", 1)
    ip = _resolve_host(game, raw_host)

    # Can't SSH to self
    if _is_self(game, ip):
        console.print_error("ssh: connect to host localhost port 22: Connection refused")
        return

    host = _find_host_anywhere(game, ip)
    if not host:
        console.print_error(t("ssh.host_not_found", ip=ip))
        return

    ssh_service = host.get_service_by_name("ssh")
    if not ssh_service:
        console.print_error(t("ssh.no_ssh", ip=ip))
        return

    def _connect(h, user_name):
        game.player.connected_to = h.ip
        game.current_host = h
        h.env["USER"] = user_name
        h.env["LOGNAME"] = user_name
        if user_name == "root":
            h.cwd = "/root"
            h.env["HOME"] = "/root"
        else:
            h.cwd = f"/home/{user_name}"
            h.env["HOME"] = f"/home/{user_name}"
        h.env["PWD"] = h.cwd
        motd = generate_motd(h.hostname, h.ip, h.os, h.users)
        console.print(f"[dim]{motd}[/dim]")

    if host.compromised:
        fake_progress(t("ssh.connecting", ip=ip), seconds=1.0)
        _connect(host, username)
        return

    cred = game.player.has_credential_for(ip, username)
    if cred:
        fake_progress(t("ssh.authenticating", user=username, ip=ip), seconds=1.5)
        host.compromised = True
        host.access_level = "user"
        _connect(host, username)
        game.check_objective("compromise_host", ip=ip)
        return

    show_access_denied(t("ssh.auth_failed", user=username, ip=ip))
    if ssh_service.credentials and username == ssh_service.credentials.get("username", ""):
        console.print_info(t("ssh.hint_creds"))


@register("disconnect", "cmd.disconnect.help", required_tool="disconnect")
def handle_disconnect(game, args):
    if game.is_on_localhost():
        console.print_warning(t("disconnect.not_connected"))
        return
    ip = game.current_host.ip
    game.return_to_localhost()
    console.print_info(t("disconnect.done", ip=ip))
