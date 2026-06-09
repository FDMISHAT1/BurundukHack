"""Advanced network tools: wget, nc/netcat, dig, nslookup, traceroute, iptables, scp, whois."""
import random
import re
from commands.registry import register
from commands.linux_cmds import _require_host, _wants_help
from commands.network_cmds import _resolve_host, _find_host_anywhere
from ui.console import console
from ui.animations import fake_progress


# -----------------------------------------------------------------------
# wget
# -----------------------------------------------------------------------
@register("wget", "cmd.wget.help", required_tool="wget")
def handle_wget(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: wget [OPTION]... [URL]...\n")
        console.print("  wget http://host/file       download file")
        console.print("  wget -O output URL          save as output")
        console.print("  wget -q URL                 quiet mode")
        console.print("  wget -c URL                 continue download")
        console.print("  wget --no-check-certificate skip SSL verify")
        return
    if not _require_host(game):
        return

    url = args[-1]
    quiet = "-q" in args
    output_file = None
    if "-O" in args:
        idx = args.index("-O")
        if idx + 1 < len(args):
            output_file = args[idx + 1]

    m = re.match(r'https?://([^/:]+)(?::(\d+))?(/.*)?', url)
    if not m:
        console.print_error(f"wget: invalid URL '{url}'")
        return 1

    hostname = m.group(1)
    path = m.group(3) or "/index.html"
    filename = path.rstrip("/").split("/")[-1] or "index.html"

    ip = _resolve_host(game, hostname)
    host = _find_host_anywhere(game, ip)

    if not quiet:
        console.print(f"--{{}}- {url}")
        console.print(f"Resolving {hostname}... {ip}")
        console.print(f"Connecting to {hostname}|{ip}|:80... connected.")
        console.print(f"HTTP request sent, awaiting response...")

    if not host:
        if not quiet:
            console.print_error("wget: unable to connect")
        return 1

    # Find file on host
    web_root = "/var/www/html"
    fpath = web_root + path
    if fpath.endswith("/"):
        fpath += "index.html"

    content = host.files.get(fpath, None)
    if content is None:
        if not quiet:
            console.print("HTTP/1.1 404 Not Found")
            console.print_error(f"wget: server returned 404")
        return 1

    if not quiet:
        console.print(f"200 OK")
        console.print(f"Length: {len(content)} ({len(content)} bytes) [text/html]")
        save_name = output_file or filename
        console.print(f"Saving to: '{save_name}'")
        fake_progress(f"Downloading {save_name}", seconds=1.5)

    # Save to local filesystem
    from commands.filesystem_cmds import _resolve_path
    save_path = output_file or filename
    if not save_path.startswith("/"):
        save_path = _resolve_path(game.current_host.cwd, save_path)
    game.current_host.files[save_path] = content
    game.current_host.user_files[save_path] = content

    if not quiet:
        console.print(f"'{output_file or filename}' saved [{len(content)}]")
    return 0


# -----------------------------------------------------------------------
# nc / netcat
# -----------------------------------------------------------------------
@register("nc", "cmd.nc.help", required_tool="nc")
def handle_nc(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: nc [OPTIONS] HOST PORT\n")
        console.print("  nc -zv host 22        check if port 22 is open")
        console.print("  nc -zv host 1-100     scan port range")
        console.print("  nc -l -p 8080         listen on port 8080")
        console.print("  nc host port          connect to host:port")
        return
    if not _require_host(game):
        return

    listen = "-l" in args
    verbose = "-v" in args
    scan = "-z" in args
    non_flag = [a for a in args if not a.startswith("-")]

    if listen:
        port = "8080"
        if "-p" in args:
            idx = args.index("-p")
            if idx + 1 < len(args):
                port = args[idx + 1]
        console.print(f"Listening on 0.0.0.0 {port}")
        console.print("[dim]Waiting for connection... (Ctrl+C to stop)[/dim]")
        return

    if len(non_flag) < 2:
        console.print_error("nc: missing host or port")
        return 1

    target = non_flag[0]
    port_spec = non_flag[1]
    ip = _resolve_host(game, target)
    host = _find_host_anywhere(game, ip)

    # Port range scan
    if "-" in port_spec:
        start, end = port_spec.split("-", 1)
        try:
            start, end = int(start), int(end)
        except ValueError:
            console.print_error("nc: invalid port range")
            return 1
        for port in range(start, min(end + 1, start + 1000)):
            open_port = False
            if host:
                for svc in host.services:
                    if svc.port == port:
                        open_port = True
                        break
            if verbose:
                if open_port:
                    console.print(f"{ip}: inverse host lookup failed:")
                    console.print(f"(UNKNOWN) [{ip}] {port} (?) [bold green]open[/bold green]")
                # closed ports: silent in scan mode
        return 0

    # Single port
    try:
        port = int(port_spec)
    except ValueError:
        console.print_error(f"nc: invalid port '{port_spec}'")
        return 1

    if scan:
        open_port = False
        if host:
            for svc in host.services:
                if svc.port == port:
                    open_port = True
                    break
        if verbose:
            if open_port:
                console.print(f"Connection to {ip} {port} port [tcp/*] succeeded!")
            else:
                console.print_error(f"nc: connect to {ip} port {port} (tcp) failed: Connection refused")
        return 0 if open_port else 1

    # Connect mode — check if port actually open
    if not host:
        console.print_error(f"nc: connect to {ip} port {port} (tcp) failed: No route to host")
        return 1

    open_port = any(svc.port == port for svc in host.services)
    if not open_port:
        console.print_error(f"nc: connect to {ip} port {port} (tcp) failed: Connection refused")
        return 1

    console.print(f"[dim]Connected to {ip}:{port}[/dim]")
    console.print(f"[dim]Type text to send, Ctrl+C to close[/dim]")
    return 0


@register("netcat", "cmd.nc.help", required_tool="netcat")
def handle_netcat(game, args):
    return handle_nc(game, args)


# -----------------------------------------------------------------------
# dig
# -----------------------------------------------------------------------
@register("dig", "cmd.dig.help", required_tool="dig")
def handle_dig(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: dig [OPTIONS] DOMAIN [TYPE]\n")
        console.print("  dig example.com          A record lookup")
        console.print("  dig example.com MX       MX record")
        console.print("  dig +short example.com   short output")
        console.print("  dig -x 1.2.3.4           reverse DNS")
        console.print("  dig @8.8.8.8 example.com use specific server")
        return
    if not _require_host(game):
        return

    short = "+short" in args
    clean = [a for a in args if not a.startswith("+") and not a.startswith("-") and not a.startswith("@")]

    domain = clean[0] if clean else "localhost"
    qtype = clean[1].upper() if len(clean) > 1 else "A"

    ip = _resolve_host(game, domain)

    if short:
        console.print(ip)
        return

    query_id = random.randint(10000, 65535)
    console.print(f"; <<>> DiG 9.16.1-Ubuntu <<>> {domain}")
    console.print(f";; global options: +cmd")
    console.print(f";; Got answer:")
    console.print(f";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: {query_id}")
    console.print(f";; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1")
    console.print()
    console.print(f";; QUESTION SECTION:")
    console.print(f";{domain}.\t\t\tIN\t{qtype}")
    console.print()
    console.print(f";; ANSWER SECTION:")
    ttl = random.randint(60, 3600)
    if qtype == "A":
        console.print(f"{domain}.\t\t{ttl}\tIN\tA\t{ip}")
    elif qtype == "MX":
        console.print(f"{domain}.\t\t{ttl}\tIN\tMX\t10 mail.{domain}.")
    elif qtype == "NS":
        console.print(f"{domain}.\t\t{ttl}\tIN\tNS\tns1.{domain}.")
        console.print(f"{domain}.\t\t{ttl}\tIN\tNS\tns2.{domain}.")
    console.print()
    console.print(f";; Query time: {random.randint(1, 50)} msec")
    console.print(f";; SERVER: 8.8.8.8#53(8.8.8.8)")
    console.print(f";; MSG SIZE  rcvd: {random.randint(50, 200)}")


# -----------------------------------------------------------------------
# nslookup
# -----------------------------------------------------------------------
@register("nslookup", "cmd.nslookup.help", required_tool="nslookup")
def handle_nslookup(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: nslookup [OPTIONS] DOMAIN [SERVER]\n")
        console.print("  nslookup example.com         lookup A record")
        console.print("  nslookup -type=MX example.com MX records")
        return
    if not _require_host(game):
        return

    domain = [a for a in args if not a.startswith("-")][0] if [a for a in args if not a.startswith("-")] else "localhost"
    ip = _resolve_host(game, domain)

    console.print(f"Server:\t\t8.8.8.8")
    console.print(f"Address:\t8.8.8.8#53\n")
    console.print(f"Non-authoritative answer:")
    console.print(f"Name:\t{domain}")
    console.print(f"Address: {ip}")


# -----------------------------------------------------------------------
# traceroute
# -----------------------------------------------------------------------
@register("traceroute", "cmd.traceroute.help", required_tool="traceroute")
def handle_traceroute(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: traceroute [OPTIONS] HOST\n")
        console.print("  traceroute host      trace route to host")
        console.print("  traceroute -m 10     max 10 hops")
        return
    if not _require_host(game):
        return

    target = args[-1]
    ip = _resolve_host(game, target)
    max_hops = 10
    if "-m" in args:
        idx = args.index("-m")
        if idx + 1 < len(args):
            try:
                max_hops = int(args[idx + 1])
            except ValueError:
                pass

    console.print(f"traceroute to {target} ({ip}), {max_hops} hops max, 60 byte packets")

    # Generate realistic hops
    my_ip = game.localhost.ip if game.localhost else "10.10.10.5"
    gw = my_ip.rsplit(".", 1)[0] + ".1"
    hops = [gw]

    # Add some ISP-like intermediate hops
    for i in range(random.randint(2, 5)):
        hops.append(f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}")
    hops.append(ip)

    for i, hop in enumerate(hops[:max_hops], 1):
        t1 = round(random.uniform(0.5, 30.0), 3)
        t2 = round(t1 + random.uniform(-2, 2), 3)
        t3 = round(t1 + random.uniform(-2, 2), 3)
        console.print(f" {i:2d}  {hop}  {t1:.3f} ms  {max(0.1, t2):.3f} ms  {max(0.1, t3):.3f} ms")
        if hop == ip:
            break


# -----------------------------------------------------------------------
# iptables
# -----------------------------------------------------------------------
@register("iptables", "cmd.iptables.help", required_tool="iptables")
def handle_iptables(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: iptables [OPTIONS]\n")
        console.print("  iptables -L                  list rules")
        console.print("  iptables -L -n               list rules (numeric)")
        console.print("  iptables -A INPUT -p tcp --dport 22 -j ACCEPT")
        console.print("  iptables -D INPUT 1          delete rule 1")
        console.print("  iptables -F                  flush all rules")
        console.print("  iptables -S                  show rules in save format")
        return
    if not _require_host(game):
        return

    host = game.current_host
    if host.access_level != "root":
        console.print_error("iptables: Permission denied (you must be root)")
        return 1

    if "-L" in args:
        console.print("Chain INPUT (policy ACCEPT)")
        console.print(f"{'target':10s} {'prot':6s} {'opt':5s} {'source':20s} {'destination'}")
        for svc in host.services:
            console.print(f"{'ACCEPT':10s} {'tcp':6s} {'--':5s} {'0.0.0.0/0':20s} 0.0.0.0/0   tcp dpt:{svc.port}")
        console.print()
        console.print("Chain FORWARD (policy DROP)")
        console.print(f"{'target':10s} {'prot':6s} {'opt':5s} {'source':20s} {'destination'}")
        console.print()
        console.print("Chain OUTPUT (policy ACCEPT)")
        console.print(f"{'target':10s} {'prot':6s} {'opt':5s} {'source':20s} {'destination'}")
    elif "-S" in args:
        console.print("-P INPUT ACCEPT")
        console.print("-P FORWARD DROP")
        console.print("-P OUTPUT ACCEPT")
        for svc in host.services:
            console.print(f"-A INPUT -p tcp --dport {svc.port} -j ACCEPT")
    elif "-F" in args:
        console.print("[dim]iptables: flushed all chains[/dim]")
    else:
        console.print("[dim]iptables: rule applied (simulated)[/dim]")
    return 0


# -----------------------------------------------------------------------
# scp
# -----------------------------------------------------------------------
@register("scp", "cmd.scp.help", required_tool="scp")
def handle_scp(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: scp [OPTIONS] SOURCE DEST\n")
        console.print("  scp file user@host:/path     upload file")
        console.print("  scp user@host:/file ./       download file")
        console.print("  scp -r dir user@host:/path   recursive")
        console.print("  scp -P 2222 file user@host:  custom port")
        return
    if not _require_host(game):
        return

    non_flag = [a for a in args if not a.startswith("-")]
    if len(non_flag) < 2:
        console.print_error("scp: missing source or destination")
        return 1

    src, dst = non_flag[0], non_flag[1]
    fake_progress(f"scp {src} → {dst}", seconds=2.0)
    console.print(f"[dim]{src} → {dst} (simulated)[/dim]")
    return 0


# -----------------------------------------------------------------------
# whois
# -----------------------------------------------------------------------
@register("whois", "cmd.whois.help", required_tool="whois")
def handle_whois(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: whois DOMAIN\n")
        console.print("  whois example.com    lookup domain info")
        console.print("  whois 8.8.8.8        lookup IP info")
        return

    target = args[0]
    console.print(f"% WHOIS lookup for: {target}")
    console.print(f"%")
    console.print(f"Domain Name: {target.upper()}")
    console.print(f"Registry Domain ID: {random.randint(100000000, 999999999)}_DOMAIN")
    console.print(f"Registrar WHOIS Server: whois.registrar.com")
    console.print(f"Registrar URL: https://www.registrar.com")
    console.print(f"Updated Date: 2024-01-15T12:00:00Z")
    console.print(f"Creation Date: 2020-03-22T10:30:00Z")
    console.print(f"Registry Expiry Date: 2025-03-22T10:30:00Z")
    console.print(f"Registrar: Example Registrar, LLC")
    console.print(f"Name Server: ns1.{target}")
    console.print(f"Name Server: ns2.{target}")
    console.print(f"DNSSEC: unsigned")
    console.print(f"")
    console.print(f"% NOTE: WHOIS data is simulated for this game.")
    return 0


# -----------------------------------------------------------------------
# telnet
# -----------------------------------------------------------------------
@register("telnet", "cmd.telnet.help", required_tool="telnet")
def handle_telnet(game, args):
    if _wants_help(args):
        console.print("Usage: telnet HOST [PORT]\n")
        console.print("  telnet host          connect to port 23")
        console.print("  telnet host 80       connect to port 80")
        return
    if not _require_host(game):
        return
    if not args:
        console.print_error("telnet: missing host operand")
        return 1

    target = args[0]
    port = int(args[1]) if len(args) > 1 else 23
    ip = _resolve_host(game, target)
    host = _find_host_anywhere(game, ip)

    console.print(f"Trying {ip}...")
    if not host:
        console.print(f"telnet: Unable to connect to remote host: Connection timed out")
        return 1
    open_port = any(svc.port == port for svc in host.services)
    if not open_port:
        console.print(f"telnet: Unable to connect to remote host: Connection refused")
        return 1
    console.print(f"Connected to {ip}.")
    console.print(f"Escape character is '^]'.")
    console.print(f"[dim]Connection closed by foreign host.[/dim]")
    return 0


# -----------------------------------------------------------------------
# socat
# -----------------------------------------------------------------------
@register("socat", "cmd.socat.help", required_tool="socat")
def handle_socat(game, args):
    if _wants_help(args) or not args or args == ["-"]:
        console.print("Usage: socat [OPTIONS] ADDRESS1 ADDRESS2\n")
        console.print("  socat TCP-LISTEN:8080,fork EXEC:/bin/bash")
        console.print("  socat TCP:host:port STDIN")
        console.print("  socat UNIX-LISTEN:/tmp/s,fork TCP:host:port")
        console.print("  socat - TCP:host:port")
        return
    if not _require_host(game):
        return

    addr1 = args[0]
    if addr1.startswith("TCP-LISTEN:"):
        port = addr1.split(":")[1].split(",")[0]
        console.print(f"[dim]socat: listening on 0.0.0.0:{port} (Ctrl+C to stop)[/dim]")
    elif addr1.startswith("TCP:"):
        parts = addr1.split(":")
        host_part = parts[1] if len(parts) > 1 else "?"
        console.print(f"[dim]socat: connected to {host_part}[/dim]")
    else:
        console.print(f"[dim]socat: relay established (simulated)[/dim]")
    return 0


# -----------------------------------------------------------------------
# arp
# -----------------------------------------------------------------------
@register("arp", "cmd.arp.help", required_tool="arp")
def handle_arp(game, args):
    if _wants_help(args):
        console.print("Usage: arp [OPTIONS]\n")
        console.print("  arp -a       display all entries")
        console.print("  arp -n       numeric output (no DNS)")
        console.print("  arp -d IP    delete an entry")
        return
    if not _require_host(game):
        return

    numeric = "-n" in args
    host = game.current_host
    my_ip = host.ip if hasattr(host, "ip") else "10.10.10.5"
    gateway = my_ip.rsplit(".", 1)[0] + ".1"

    def _mac():
        return ":".join(f"{random.randint(0,255):02x}" for _ in range(6))

    entries = [(gateway, _mac(), "eth0")]
    base = my_ip.rsplit(".", 1)[0]
    for _ in range(random.randint(2, 3)):
        ip = f"{base}.{random.randint(2, 254)}"
        entries.append((ip, _mac(), "eth0"))

    if "-d" in args:
        console.print("[dim]arp: entry deleted (simulated)[/dim]")
        return 0

    for ip_addr, mac, iface in entries:
        if numeric or "-a" not in args:
            console.print(f"? ({ip_addr}) at {mac} \\[ether] on {iface}")
        else:
            name = f"host-{ip_addr.split('.')[-1]}" if ip_addr != gateway else "_gateway"
            console.print(f"{name} ({ip_addr}) at {mac} \\[ether] on {iface}")
    return 0


# -----------------------------------------------------------------------
# tcpdump
# -----------------------------------------------------------------------
@register("tcpdump", "cmd.tcpdump.help", required_tool="tcpdump")
def handle_tcpdump(game, args):
    if _wants_help(args):
        console.print("Usage: tcpdump [OPTIONS] [FILTER]\n")
        console.print("  tcpdump              capture packets (default 5)")
        console.print("  tcpdump -c 10        capture 10 packets")
        console.print("  tcpdump -i eth0      listen on interface")
        console.print("  tcpdump -n           numeric output")
        console.print("  tcpdump port 443     filter by port")
        return
    if not _require_host(game):
        return

    host = game.current_host
    if hasattr(host, "access_level") and host.access_level != "root":
        console.print_error("tcpdump: You don't have permission to capture on that device")
        console.print_error("(socket: Operation not permitted)")
        return 1

    count = 5
    if "-c" in args:
        idx = args.index("-c")
        if idx + 1 < len(args):
            try:
                count = int(args[idx + 1])
            except ValueError:
                pass
    count = min(count, 50)

    numeric = "-n" in args
    iface = "eth0"
    if "-i" in args:
        idx = args.index("-i")
        if idx + 1 < len(args):
            iface = args[idx + 1]

    my_ip = host.ip if hasattr(host, "ip") else "192.168.1.100"
    console.print(f"tcpdump: verbose output suppressed, use -v for full decode")
    console.print(f"listening on {iface}, link-type EN10MB (Ethernet), capture size 262144 bytes")

    flags_choices = ["S", "S.", ".", "P.", "F.", "R."]
    for i in range(count):
        h = random.randint(0, 23)
        m = random.randint(0, 59)
        s = random.randint(0, 59)
        us = random.randint(0, 999999)
        src_ip = my_ip if random.random() < 0.5 else f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        dst_ip = my_ip if src_ip != my_ip else f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        sp = random.randint(1024, 65535)
        dp = random.choice([22, 53, 80, 443, 8080, 3306])
        flags = random.choice(flags_choices)
        seq = random.randint(100000, 9999999)
        length = random.randint(0, 1460)
        console.print(f"{h:02d}:{m:02d}:{s:02d}.{us:06d} IP {src_ip}.{sp} > {dst_ip}.{dp}: Flags [{flags}], seq {seq}, length {length}")

    console.print(f"\n{count} packets captured")
    console.print(f"{count} packets received by filter")
    console.print(f"0 packets dropped by kernel")
    return 0


# -----------------------------------------------------------------------
# ssh-agent
# -----------------------------------------------------------------------
@register("ssh-agent", "cmd.ssh-agent.help", required_tool="ssh-agent")
def handle_ssh_agent(game, args):
    if _wants_help(args):
        console.print("Usage: ssh-agent [OPTIONS]\n")
        console.print("  ssh-agent         start agent, print env vars")
        console.print("  ssh-agent -k      kill the current agent")
        return
    if not _require_host(game):
        return

    if "-k" in args:
        console.print("unset SSH_AUTH_SOCK;")
        console.print("unset SSH_AGENT_PID;")
        console.print("echo Agent pid killed;")
        return 0

    pid = random.randint(10000, 65000)
    sock = f"/tmp/ssh-XXXX{random.randint(1000,9999)}/agent.{pid - 1}"
    console.print(f"SSH_AUTH_SOCK={sock}; export SSH_AUTH_SOCK;")
    console.print(f"SSH_AGENT_PID={pid}; export SSH_AGENT_PID;")
    console.print(f"echo Agent pid {pid};")

    # Set env vars on the host
    host = game.current_host
    if hasattr(host, "env"):
        host.env["SSH_AUTH_SOCK"] = sock
        host.env["SSH_AGENT_PID"] = str(pid)
    return 0


# -----------------------------------------------------------------------
# ssh-add
# -----------------------------------------------------------------------
@register("ssh-add", "cmd.ssh-add.help", required_tool="ssh-add")
def handle_ssh_add(game, args):
    if _wants_help(args):
        console.print("Usage: ssh-add [OPTIONS] [FILE]\n")
        console.print("  ssh-add              add default key (~/.ssh/id_rsa)")
        console.print("  ssh-add FILE         add specific key")
        console.print("  ssh-add -l           list fingerprints of keys")
        console.print("  ssh-add -D           delete all identities")
        return
    if not _require_host(game):
        return

    host = game.current_host
    user = host.access_level if hasattr(host, "access_level") else "user"
    home = "/root" if user == "root" else f"/home/{user}"

    if "-D" in args:
        console.print("All identities removed.")
        return 0

    if "-l" in args:
        bits = random.choice([2048, 3072, 4096])
        fp = ":".join(f"{random.randint(0,255):02x}" for _ in range(16))
        console.print(f"{bits} SHA256:{fp} {user}@{host.hostname if hasattr(host, 'hostname') else 'localhost'} (RSA)")
        return 0

    keyfile = args[0] if args else f"{home}/.ssh/id_rsa"
    console.print(f"Identity added: {keyfile}")
    return 0


# -----------------------------------------------------------------------
# mtr
# -----------------------------------------------------------------------
@register("mtr", "cmd.mtr.help", required_tool="mtr")
def handle_mtr(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: mtr [OPTIONS] HOST\n")
        console.print("  mtr host             traceroute with statistics")
        console.print("  mtr -r host          report mode")
        console.print("  mtr -c 10 host       send 10 pings per hop")
        return
    if not _require_host(game):
        return

    target = [a for a in args if not a.startswith("-")]
    if not target:
        console.print_error("mtr: missing host operand")
        return 1
    target = target[-1]
    ip = _resolve_host(game, target)

    my_ip = game.localhost.ip if game.localhost else "10.10.10.5"
    gateway = my_ip.rsplit(".", 1)[0] + ".1"
    hops = [gateway]
    for _ in range(random.randint(3, 4)):
        hops.append(f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}")
    hops.append(ip)

    console.print(f"                             My traceroute  [v0.95]")
    console.print(f"{'Host':>40s}       Loss%   Snt    Last    Avg   Best   Wrst  StDev")
    for i, hop in enumerate(hops, 1):
        loss = 0.0 if random.random() > 0.1 else round(random.uniform(1, 5), 1)
        snt = 10
        best = round(random.uniform(0.5, 15.0), 1)
        avg = round(best + random.uniform(0, 10), 1)
        last = round(avg + random.uniform(-3, 3), 1)
        worst = round(avg + random.uniform(5, 30), 1)
        stdev = round(random.uniform(0.1, 8.0), 1)
        console.print(f" {i:2d}.|-- {hop:<34s} {loss:5.1f}%  {snt:4d}  {max(0.1,last):6.1f}  {avg:6.1f}  {best:6.1f}  {worst:6.1f}  {stdev:5.1f}")
    return 0
