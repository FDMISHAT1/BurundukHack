"""CTF / forensics / steganography tools."""
import hashlib
import base64 as b64lib
import re
from commands.registry import register
from commands.filesystem_cmds import _resolve_path
from ui.console import console
from ui.lang import t


def _require_host(game) -> bool:
    if not game.current_host:
        console.print_error(t("fs.not_connected"))
        return False
    return True


def _get_file(game, args, cmd_name: str) -> str | None:
    """Resolve file path from args, return content or None."""
    if not _require_host(game):
        return None
    if not args or args[-1].startswith("-"):
        console.print_error(f"{cmd_name}: missing file operand")
        return None
    filepath = args[-1]
    if not filepath.startswith("/"):
        filepath = _resolve_path(game.current_host.cwd, filepath)
    if filepath not in game.current_host.files:
        console.print_error(f"{cmd_name}: {filepath}: No such file or directory")
        return None
    return game.current_host.files[filepath]


# -----------------------------------------------------------------------
#  strings — extract printable strings from file
# -----------------------------------------------------------------------

@register("strings", "cmd.strings.help", required_tool="strings")
def handle_strings(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: strings [OPTIONS] FILE\n")
        console.print("  strings file       print sequences of printable characters (min 4)")
        console.print("  strings -n 8 file  minimum string length 8")
        return
    content = _get_file(game, args, "strings")
    if content is None:
        return
    min_len = 4
    if "-n" in args:
        idx = args.index("-n")
        if idx + 1 < len(args):
            try:
                min_len = int(args[idx + 1])
            except ValueError:
                pass
    # Extract printable sequences
    for match in re.finditer(r'[\x20-\x7e]{' + str(min_len) + r',}', content):
        console.print(match.group())


# -----------------------------------------------------------------------
#  xxd — hex dump
# -----------------------------------------------------------------------

@register("xxd", "cmd.xxd.help", required_tool="xxd")
def handle_xxd(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: xxd [OPTIONS] FILE\n")
        console.print("  xxd file           hex dump of file")
        console.print("  xxd -l 64 file     show only first 64 bytes")
        return
    content = _get_file(game, args, "xxd")
    if content is None:
        return
    data = content.encode("utf-8", errors="replace")
    limit = len(data)
    if "-l" in args:
        idx = args.index("-l")
        if idx + 1 < len(args):
            try:
                limit = int(args[idx + 1])
            except ValueError:
                pass
    data = data[:limit]
    for offset in range(0, len(data), 16):
        chunk = data[offset:offset + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        console.print(f"{offset:08x}: {hex_part:<48s}  {ascii_part}")


# -----------------------------------------------------------------------
#  file — identify file type
# -----------------------------------------------------------------------

@register("file", "cmd.file.help", required_tool="file")
def handle_file(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: file FILE...\n")
        console.print("  file image.png     determine file type")
        return
    content = _get_file(game, args, "file")
    if content is None:
        return
    filepath = args[-1]
    # Guess type from content/name
    if content.startswith("[ELF "):
        ftype = "ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked"
    elif content.startswith("[binary"):
        ftype = "data"
    elif content.startswith("[device"):
        ftype = "character special"
    elif content.startswith("[DATABASE"):
        ftype = "MySQL database file, version 5.7"
    elif filepath.endswith(".py"):
        ftype = "Python script, ASCII text executable"
    elif filepath.endswith(".sh"):
        ftype = "Bourne-Again shell script, ASCII text executable"
    elif filepath.endswith(".conf") or filepath.endswith(".cfg") or filepath.endswith(".ini"):
        ftype = "ASCII text (configuration file)"
    elif filepath.endswith(".log"):
        ftype = "ASCII text (log file)"
    elif filepath.endswith(".png"):
        ftype = "PNG image data, 800 x 600, 8-bit/color RGBA, non-interlaced"
    elif filepath.endswith(".jpg") or filepath.endswith(".jpeg"):
        ftype = "JPEG image data, JFIF standard 1.01, resolution (DPI)"
    elif filepath.endswith(".zip"):
        ftype = "Zip archive data, at least v2.0 to extract"
    elif filepath.endswith(".gz"):
        ftype = "gzip compressed data"
    elif filepath.endswith(".db"):
        ftype = "SQLite 3.x database, last written using SQLite version 3039004"
    elif "BEGIN" in content and "KEY" in content:
        ftype = "PEM RSA private key"
    elif content.startswith("{") or content.startswith("["):
        ftype = "JSON data, ASCII text"
    elif content.startswith("<?xml") or content.startswith("<html"):
        ftype = "HTML document, ASCII text"
    elif content.startswith("#!/"):
        ftype = "shell script, ASCII text executable"
    else:
        ftype = "ASCII text"
    console.print(f"{filepath}: {ftype}")


# -----------------------------------------------------------------------
#  base64 — encode/decode
# -----------------------------------------------------------------------

@register("base64", "cmd.base64.help", required_tool="base64")
def handle_base64(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: base64 [OPTIONS] [FILE]\n")
        console.print("  base64 file        encode file to base64")
        console.print("  base64 -d file     decode base64 file")
        console.print("  echo text | base64 (use echo + base64 for strings)")
        return
    if not _require_host(game):
        return

    decode_mode = "-d" in args or "--decode" in args
    clean_args = [a for a in args if not a.startswith("-")]

    if not clean_args:
        if game.stdin:
            content = game.stdin
        else:
            console.print_error("base64: missing file operand")
            return
    else:
        content = _get_file(game, args, "base64")
    if content is None:
        return

    if decode_mode:
        try:
            decoded = b64lib.b64decode(content.strip()).decode("utf-8", errors="replace")
            console.print(decoded)
        except Exception:
            console.print_error("base64: invalid input")
    else:
        encoded = b64lib.b64encode(content.encode()).decode()
        # Print in 76-char lines like real base64
        for i in range(0, len(encoded), 76):
            console.print(encoded[i:i + 76])


# -----------------------------------------------------------------------
#  md5sum / sha256sum — hash files
# -----------------------------------------------------------------------

@register("md5sum", "cmd.md5sum.help", required_tool="md5sum")
def handle_md5sum(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: md5sum FILE...\n")
        console.print("  md5sum file.txt    compute MD5 hash")
        return
    clean = [a for a in args if not a.startswith("-")]
    if not clean and game.stdin:
        content = game.stdin
        name = "-"
    else:
        content = _get_file(game, args, "md5sum")
        name = clean[-1] if clean else "-"
        if content is None:
            return
    h = hashlib.md5(content.encode()).hexdigest()
    console.print(f"{h}  {name}")


@register("sha256sum", "cmd.sha256sum.help", required_tool="sha256sum")
def handle_sha256sum(game, args):
    if args and args[0] in ("-h", "--help"):
        console.print("Usage: sha256sum FILE...\n")
        console.print("  sha256sum file.txt    compute SHA-256 hash")
        return
    clean = [a for a in args if not a.startswith("-")]
    if not clean and game.stdin:
        content = game.stdin
        name = "-"
    else:
        content = _get_file(game, args, "sha256sum")
        name = clean[-1] if clean else "-"
        if content is None:
            return
    h = hashlib.sha256(content.encode()).hexdigest()
    console.print(f"{h}  {name}")


# -----------------------------------------------------------------------
#  binwalk — firmware/file analysis
# -----------------------------------------------------------------------

@register("binwalk", "cmd.binwalk.help", required_tool="binwalk")
def handle_binwalk(game, args):
    if not args or args[0] in ("-h", "--help"):
        console.print("Usage: binwalk [OPTIONS] FILE\n")
        console.print("  binwalk file       scan for embedded files/data")
        console.print("  binwalk -e file    extract embedded files")
        return
    content = _get_file(game, args, "binwalk")
    if content is None:
        return
    filepath = args[-1]
    console.print(f"\n{'DECIMAL':>10s} {'HEXADECIMAL':>14s} {'DESCRIPTION'}")
    console.print("-" * 60)
    offset = 0
    if "BEGIN" in content:
        console.print(f"{offset:>10d} {'0x0':>14s} PEM certificate/key data")
    if "ELF" in content or content.startswith("[ELF"):
        console.print(f"{offset:>10d} {'0x0':>14s} ELF 64-bit LSB executable, x86-64")
    if "PK" in content or filepath.endswith(".zip"):
        console.print(f"{offset:>10d} {'0x0':>14s} Zip archive data, v2.0")
    if "#!/" in content:
        console.print(f"{offset:>10d} {'0x0':>14s} Shell script")
    if "<?php" in content:
        console.print(f"{offset:>10d} {'0x0':>14s} PHP script")
    if "SQL" in content or "mysql" in content.lower() or filepath.endswith(".db"):
        console.print(f"{offset:>10d} {'0x0':>14s} SQLite/MySQL database")
    if content.strip() and not any(k in content for k in ["ELF", "PK", "#!/", "<?php", "SQL", "BEGIN"]):
        console.print(f"{offset:>10d} {'0x0':>14s} ASCII text data, {len(content)} bytes")
    console.print()


# -----------------------------------------------------------------------
#  steghide — steganography
# -----------------------------------------------------------------------

@register("steghide", "cmd.steghide.help", required_tool="steghide")
def handle_steghide(game, args):
    if not args or args[0] in ("-h", "--help"):
        console.print("Usage: steghide COMMAND [OPTIONS]\n")
        console.print("  steghide info file.jpg          show info about cover file")
        console.print("  steghide extract -sf file.jpg   extract hidden data")
        console.print("  steghide embed -cf img -ef data embed data into image")
        return
    if not _require_host(game):
        return

    subcmd = args[0]
    if subcmd == "info":
        if len(args) < 2:
            console.print_error("steghide: missing file argument")
            return
        filepath = args[1]
        if not filepath.startswith("/"):
            filepath = _resolve_path(game.current_host.cwd, filepath)
        if filepath not in game.current_host.files:
            console.print_error(f"steghide: {filepath}: No such file")
            return
        content = game.current_host.files[filepath]
        has_hidden = "[STEG:" in content
        console.print(f'  "{filepath}":')
        console.print(f"    format: jpeg/png")
        console.print(f"    capacity: {len(content) * 3} bytes")
        if has_hidden:
            console.print(f"    embedded data: [bold yellow]yes[/bold yellow]")
        else:
            console.print(f"    embedded data: no")

    elif subcmd == "extract":
        sf_file = None
        if "-sf" in args:
            idx = args.index("-sf")
            if idx + 1 < len(args):
                sf_file = args[idx + 1]
        if not sf_file:
            console.print_error("steghide: missing -sf <file> argument")
            return
        if not sf_file.startswith("/"):
            sf_file = _resolve_path(game.current_host.cwd, sf_file)
        if sf_file not in game.current_host.files:
            console.print_error(f"steghide: {sf_file}: No such file")
            return
        content = game.current_host.files[sf_file]
        # Extract [STEG:...] markers
        match = re.search(r'\[STEG:(.*?)\]', content)
        if match:
            hidden = match.group(1)
            console.print_success(f"extracted data: \"{hidden}\"")
        else:
            console.print_error("steghide: could not extract any data")
    else:
        console.print_error(f"steghide: unknown command '{subcmd}'")


# -----------------------------------------------------------------------
#  exiftool — metadata extraction
# -----------------------------------------------------------------------

@register("exiftool", "cmd.exiftool.help", required_tool="exiftool")
def handle_exiftool(game, args):
    if not args or args[0] in ("-h", "--help"):
        console.print("Usage: exiftool [OPTIONS] FILE\n")
        console.print("  exiftool image.jpg    show all metadata")
        return
    content = _get_file(game, args, "exiftool")
    if content is None:
        return
    filepath = args[-1]
    # Generate realistic EXIF data
    console.print(f"ExifTool Version Number         : 12.76")
    console.print(f"File Name                       : {filepath.split('/')[-1]}")
    console.print(f"File Size                       : {len(content)} bytes")
    if filepath.endswith((".jpg", ".jpeg", ".png")):
        console.print(f"File Type                       : JPEG" if "jpg" in filepath else f"File Type                       : PNG")
        console.print(f"Image Width                     : 800")
        console.print(f"Image Height                    : 600")
        console.print(f"Camera Model Name               : Canon EOS 5D Mark IV")
        console.print(f"GPS Latitude                    : 55 deg 45' 8.16\" N")
        console.print(f"GPS Longitude                   : 37 deg 37' 4.08\" E")
        # Check for hidden metadata markers
        match = re.search(r'\[EXIF:(.*?)\]', content)
        if match:
            console.print(f"[bold yellow]Comment                         : {match.group(1)}[/bold yellow]")
    else:
        console.print(f"File Type                       : text")
        console.print(f"MIME Type                       : text/plain")


# -----------------------------------------------------------------------
#  curl — HTTP client
# -----------------------------------------------------------------------

@register("curl", "cmd.curl.help", required_tool="curl")
def handle_curl(game, args):
    if not args or args[0] in ("-h", "--help"):
        console.print("Usage: curl [OPTIONS] URL\n")
        console.print("  curl http://host/path           GET request")
        console.print("  curl -I http://host             headers only")
        console.print("  curl -d 'data' http://host      POST request")
        console.print("  curl -X PUT http://host         custom method")
        console.print("  curl -H 'Header: val' URL       custom header")
        console.print("  curl -o file URL                save to file")
        console.print("  curl -v URL                     verbose output")
        console.print("  curl -L URL                     follow redirects")
        console.print("  curl -k URL                     skip SSL verify")
        console.print("  curl -u user:pass URL           basic auth")
        return
    if not _require_host(game):
        return

    # Parse all curl flags
    headers_only = "-I" in args or "--head" in args
    verbose = "-v" in args
    method = "GET"
    post_data = None
    custom_headers = []
    output_file = None
    url = None

    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-d", "--data") and i + 1 < len(args):
            post_data = args[i + 1]
            method = "POST"
            i += 2; continue
        elif a in ("-X", "--request") and i + 1 < len(args):
            method = args[i + 1].upper()
            i += 2; continue
        elif a in ("-H", "--header") and i + 1 < len(args):
            custom_headers.append(args[i + 1])
            i += 2; continue
        elif a in ("-o", "--output") and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2; continue
        elif a in ("-u", "--user") and i + 1 < len(args):
            custom_headers.append(f"Authorization: Basic {args[i+1]}")
            i += 2; continue
        elif a.startswith("-"):
            i += 1; continue
        else:
            url = a
            i += 1

    if not url:
        console.print_error("curl: no URL specified")
        return

    m = re.match(r'https?://([^/:]+)(?::(\d+))?(/.*)?', url)
    if not m:
        console.print_error(f"curl: (6) Could not resolve host: {url}")
        return

    hostname_or_ip = m.group(1)
    port = int(m.group(2)) if m.group(2) else 80
    path = m.group(3) or "/"

    host = _find_host_anywhere_for_curl(game, hostname_or_ip)
    if not host:
        console.print_error(f"curl: (7) Failed to connect to {hostname_or_ip} port {port}")
        return

    if verbose:
        console.print(f"*   Trying {host.ip}:{port}...")
        console.print(f"* Connected to {hostname_or_ip} ({host.ip}) port {port}")
        console.print(f"> {method} {path} HTTP/1.1")
        console.print(f"> Host: {hostname_or_ip}")
        console.print(f"> User-Agent: curl/7.68.0")
        for h in custom_headers:
            console.print(f"> {h}")
        if post_data:
            console.print(f"> Content-Length: {len(post_data)}")
        console.print(f">")

    if headers_only or verbose:
        console.print(f"< HTTP/1.1 200 OK")
        console.print(f"< Server: Apache/2.4.41 (Ubuntu)")
        console.print(f"< Content-Type: text/html; charset=UTF-8")
        if headers_only:
            return

    # Find content
    content = None
    web_roots = ["/var/www/html"]
    for root in web_roots:
        fpath = root + path
        if fpath.endswith("/"):
            fpath += "index.html"
        if fpath in host.files:
            content = host.files[fpath]
            break

    if content is None:
        content = "<html><body><h1>404 Not Found</h1></body></html>"

    if output_file:
        from commands.filesystem_cmds import _resolve_path
        fp = output_file if output_file.startswith("/") else _resolve_path(game.current_host.cwd, output_file)
        from commands.file_edit_cmds import _track_file
        _track_file(game.current_host, fp, content)
        console.print(f"[dim]  % Total    % Received  Avg Speed   Time[/dim]")
        console.print(f"[dim]  {len(content):>5d}       {len(content):>5d}      1234k   0:00:00[/dim]")
    else:
        console.print(content)


def _find_host_anywhere_for_curl(game, hostname_or_ip):
    """Find host by IP or hostname."""
    for net in game.networks.values():
        for host in net.hosts:
            if host.ip == hostname_or_ip or host.hostname == hostname_or_ip:
                return host
    return None
