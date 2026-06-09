"""System admin & utility commands: stat, du, ln, chown, passwd, useradd, top, lsblk, lsof, crontab, tar, zip, gzip, diff, printf, column, od, nl."""
import random
import re
import hashlib
from commands.registry import register
from commands.linux_cmds import _require_host, _wants_help, _get_input
from commands.filesystem_cmds import _resolve_path
from ui.console import console


@register("stat", "cmd.stat.help", required_tool="stat")
def handle_stat(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: stat [OPTION]... FILE...\n  stat file    display file status")
        return
    if not _require_host(game): return
    host = game.current_host
    for a in args:
        if a.startswith("-"): continue
        fp = a if a.startswith("/") else _resolve_path(host.cwd, a)
        if fp not in host.files:
            prefix = fp.rstrip("/") + "/"
            is_dir = any(f.startswith(prefix) for f in host.files)
            if not is_dir:
                console.print_error(f"stat: cannot stat '{a}': No such file or directory")
                continue
        m = host.file_meta.get(fp, {})
        content = host.files.get(fp, "")
        size = len(content.encode()) if fp in host.files else 4096
        inode = abs(hash(fp)) % 999999 + 100000
        console.print(f"  File: {fp}")
        console.print(f"  Size: {size}\t\tBlocks: {(size//512)+1}\tIO Block: 4096\t{'directory' if fp not in host.files else 'regular file'}")
        console.print(f"Device: 801h/2049d\tInode: {inode}\tLinks: 1")
        console.print(f"Access: ({m.get('perms','-rw-r--r--')})\tUid: (    0/    {m.get('owner','root')})\tGid: (    0/    {m.get('group','root')})")
        console.print(f"Access: 2024-11-15 14:32:01.000000000 +0000")
        console.print(f"Modify: 2024-11-15 14:32:01.000000000 +0000")
        console.print(f"Change: 2024-11-15 14:32:01.000000000 +0000")
        console.print(f" Birth: -")


@register("du", "cmd.du.help", required_tool="du")
def handle_du(game, args):
    if "--help" in args:
        console.print("Usage: du [OPTION]... [FILE]...\n  du -sh /etc   summary, human-readable\n  du -d 1 /     depth 1")
        return
    if not _require_host(game): return
    host = game.current_host
    summary = "-s" in args
    human = "-h" in args
    dirs = [a for a in args if not a.startswith("-")]
    if not dirs: dirs = [host.cwd]

    for d in dirs:
        dp = d if d.startswith("/") else _resolve_path(host.cwd, d)
        prefix = dp.rstrip("/") + "/" if dp != "/" else "/"
        total = sum(len(host.files[f].encode()) for f in host.files if f.startswith(prefix))
        if human:
            if total > 1048576: s = f"{total/1048576:.1f}M"
            elif total > 1024: s = f"{total/1024:.1f}K"
            else: s = f"{total}"
        else:
            s = str(total // 1024)
        console.print(f"{s}\t{dp}")


@register("ln", "cmd.ln.help", required_tool="ln")
def handle_ln(game, args):
    if _wants_help(args):
        console.print("Usage: ln [OPTION]... TARGET LINK_NAME\n  ln -s target link   create symlink\n  ln target link      create hard link")
        return
    if not _require_host(game): return
    host = game.current_host
    sym = "-s" in args
    non_flag = [a for a in args if not a.startswith("-")]
    if len(non_flag) < 2:
        console.print_error("ln: missing file operand")
        return
    target = non_flag[0] if non_flag[0].startswith("/") else _resolve_path(host.cwd, non_flag[0])
    link = non_flag[1] if non_flag[1].startswith("/") else _resolve_path(host.cwd, non_flag[1])
    if target not in host.files:
        console.print_error(f"ln: failed to access '{non_flag[0]}': No such file or directory")
        return
    host.files[link] = host.files[target]
    host.user_files[link] = host.files[target]
    m = host.file_meta.get(target, {}).copy()
    if sym:
        m["perms"] = "lrwxrwxrwx"
    host.file_meta[link] = m


@register("chown", "cmd.chown.help", required_tool="chown")
def handle_chown(game, args):
    if _wants_help(args):
        console.print("Usage: chown [OPTION]... OWNER[:GROUP] FILE...\n  chown user:group file\n  chown -R user dir")
        return
    if not _require_host(game): return
    host = game.current_host
    if host.access_level != "root":
        console.print_error("chown: Operation not permitted")
        return 1
    recursive = "-R" in args
    non_flag = [a for a in args if not a.startswith("-")]
    if len(non_flag) < 2:
        console.print_error("chown: missing operand")
        return
    spec = non_flag[0]
    files = non_flag[1:]
    owner = spec.split(":")[0] if ":" in spec else spec
    group = spec.split(":")[1] if ":" in spec else owner
    for f in files:
        fp = f if f.startswith("/") else _resolve_path(host.cwd, f)
        if fp in host.file_meta:
            host.file_meta[fp]["owner"] = owner
            host.file_meta[fp]["group"] = group
        if recursive:
            prefix = fp.rstrip("/") + "/"
            for ff in host.files:
                if ff.startswith(prefix) and ff in host.file_meta:
                    host.file_meta[ff]["owner"] = owner
                    host.file_meta[ff]["group"] = group


@register("passwd", "cmd.passwd.help", required_tool="passwd")
def handle_passwd(game, args):
    if _wants_help(args):
        console.print("Usage: passwd [OPTIONS] [USER]\n  passwd          change own password\n  passwd user     change user's password (root)")
        return
    if not _require_host(game): return
    user = args[0] if args and not args[0].startswith("-") else game.current_host.get_current_user()
    if user != game.current_host.get_current_user() and game.current_host.access_level != "root":
        console.print_error(f"passwd: You may not view or modify password information for {user}.")
        return 1
    console.print(f"Changing password for {user}.")
    try:
        console.input("Current password: ")
        console.input("New password: ")
        console.input("Retype new password: ")
    except (EOFError, KeyboardInterrupt):
        console.print()
        return
    console.print("passwd: password updated successfully")


@register("useradd", "cmd.useradd.help", required_tool="useradd")
def handle_useradd(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: useradd [OPTIONS] LOGIN\n  useradd -m -s /bin/bash user\n  -m create home\n  -s shell\n  -G groups")
        return
    if not _require_host(game): return
    if game.current_host.access_level != "root":
        console.print_error("useradd: Permission denied.")
        return 1
    name = [a for a in args if not a.startswith("-")][-1] if [a for a in args if not a.startswith("-")] else None
    if not name:
        console.print_error("useradd: missing login name")
        return
    create_home = "-m" in args
    host = game.current_host
    # Add to passwd
    passwd = host.files.get("/etc/passwd", "")
    uid = 1000 + len([l for l in passwd.split("\n") if l.strip()])
    passwd += f"\n{name}:x:{uid}:{uid}:{name}:/home/{name}:/bin/bash"
    host.files["/etc/passwd"] = passwd
    host.user_files["/etc/passwd"] = passwd
    if create_home:
        from commands.file_edit_cmds import _track_file
        _track_file(host, f"/home/{name}/.bashrc", "# .bashrc\n")
        _track_file(host, f"/home/{name}/.profile", "# .profile\n")
    console.print(f"[dim]useradd: user '{name}' created (uid={uid})[/dim]")


@register("top", "cmd.top.help", required_tool="top")
def handle_top(game, args):
    if _wants_help(args):
        console.print("Usage: top [OPTIONS]\n  top         interactive (single snapshot)\n  top -n 1    single iteration")
        return
    if not _require_host(game): return
    host = game.current_host
    user = host.get_current_user()
    up_days = random.randint(1, 365)
    load = [f"0.{random.randint(0,99):02d}" for _ in range(3)]
    mem_total = random.randint(4000, 16000)
    mem_used = random.randint(mem_total//4, mem_total*3//4)
    mem_free = mem_total - mem_used
    tasks = random.randint(80, 250)
    console.print(f"top - 14:32:01 up {up_days} days, load average: {', '.join(load)}")
    console.print(f"Tasks: {tasks} total,   1 running, {tasks-1} sleeping,   0 stopped,   0 zombie")
    console.print(f"%Cpu(s):  {random.uniform(0,15):.1f} us,  {random.uniform(0,5):.1f} sy,  0.0 ni, {random.uniform(70,95):.1f} id")
    console.print(f"MiB Mem : {mem_total:>8d} total, {mem_free:>8d} free, {mem_used:>8d} used, {random.randint(500,2000):>8d} buff/cache")
    console.print(f"MiB Swap: {mem_total//2:>8d} total, {mem_total//2:>8d} free,        0 used.")
    console.print()
    console.print(f"{'PID':>7s} {'USER':10s} {'PR':>3s} {'NI':>3s} {'VIRT':>8s} {'RES':>7s} {'SHR':>7s} {'S':1s} {'%CPU':>5s} {'%MEM':>5s} {'COMMAND'}")
    procs = [("1", "root", "20", "0", "169M", "13M", "8M", "S", "0.0", "0.1", "systemd")]
    for svc in host.services:
        pid = str(random.randint(500, 5000))
        mem = f"{random.randint(5,200)}M"
        cpu = f"{random.uniform(0,5):.1f}"
        procs.append((pid, "root", "20", "0", mem, mem, f"{random.randint(1,10)}M", "S", cpu, f"{random.uniform(0,5):.1f}", svc.name))
    procs.append((str(random.randint(5000,9000)), user, "20", "0", "25M", "6M", "3M", "S", "0.0", "0.0", "bash"))
    procs.append((str(random.randint(9000,9999)), user, "20", "0", "3M", "1M", "0M", "R", "0.3", "0.0", "top"))
    for p in procs:
        console.print(f"{p[0]:>7s} {p[1]:10s} {p[2]:>3s} {p[3]:>3s} {p[4]:>8s} {p[5]:>7s} {p[6]:>7s} {p[7]:1s} {p[8]:>5s} {p[9]:>5s} {p[10]}")


@register("lsblk", "cmd.lsblk.help", required_tool="lsblk")
def handle_lsblk(game, args):
    if _wants_help(args):
        console.print("Usage: lsblk [OPTIONS]\n  lsblk       list block devices")
        return
    console.print(f"{'NAME':10s} {'MAJ:MIN':>7s} {'RM':>3s} {'SIZE':>6s} {'RO':>3s} {'TYPE':6s} {'MOUNTPOINT'}")
    size = random.randint(20, 500)
    console.print(f"{'sda':10s} {'8:0':>7s} {'0':>3s} {f'{size}G':>6s} {'0':>3s} {'disk':6s}")
    console.print(f"{'├─sda1':10s} {'8:1':>7s} {'0':>3s} {f'{size-2}G':>6s} {'0':>3s} {'part':6s} /")
    console.print(f"{'└─sda2':10s} {'8:2':>7s} {'0':>3s} {'2G':>6s} {'0':>3s} {'part':6s} [SWAP]")


@register("lsof", "cmd.lsof.help", required_tool="lsof")
def handle_lsof(game, args):
    if _wants_help(args):
        console.print("Usage: lsof [OPTIONS]\n  lsof           list open files\n  lsof -i :80    show port 80\n  lsof -u user   files by user\n  lsof -p PID    files by PID")
        return
    if not _require_host(game): return
    host = game.current_host
    port_filter = None
    if "-i" in args:
        idx = args.index("-i")
        if idx + 1 < len(args):
            pf = args[idx + 1]
            if pf.startswith(":"):
                try: port_filter = int(pf[1:])
                except ValueError: pass

    console.print(f"{'COMMAND':12s} {'PID':>6s} {'USER':10s} {'FD':>4s} {'TYPE':6s} {'DEVICE':>12s} {'SIZE/OFF':>10s} {'NODE':>6s} {'NAME'}")
    for svc in host.services:
        if port_filter and svc.port != port_filter: continue
        pid = str(random.randint(500, 5000))
        console.print(f"{svc.name:12s} {pid:>6s} {'root':10s} {'3u':>4s} {'IPv4':6s} {str(random.randint(10000,99999)):>12s} {'0t0':>10s} {'TCP':>6s} *:{svc.port} (LISTEN)")


@register("crontab", "cmd.crontab.help", required_tool="crontab")
def handle_crontab(game, args):
    if _wants_help(args):
        console.print("Usage: crontab [OPTIONS]\n  crontab -l    list cron jobs\n  crontab -e    edit (use nano)\n  crontab -r    remove all jobs")
        return
    if not _require_host(game): return
    if "-l" in args:
        cron = game.current_host.files.get("/etc/crontab", "")
        if cron: console.print(cron)
        else: console.print("no crontab for " + game.current_host.get_current_user())
    elif "-r" in args:
        console.print("[dim]crontab: removed[/dim]")
    elif "-e" in args:
        console.print("[dim]Use: nano /etc/crontab[/dim]")
    else:
        console.print("crontab: usage error")


@register("tar", "cmd.tar.help", required_tool="tar")
def handle_tar(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: tar [OPTIONS] [FILE]...\n  tar -czf archive.tar.gz dir/    create gzip archive\n  tar -xzf archive.tar.gz         extract\n  tar -tf archive.tar.gz           list contents")
        return
    if not _require_host(game): return
    host = game.current_host
    flags = "".join(a.lstrip("-") for a in args if a.startswith("-"))
    files = [a for a in args if not a.startswith("-")]

    if "t" in flags and files:
        # List archive
        fp = files[0] if files[0].startswith("/") else _resolve_path(host.cwd, files[0])
        if fp in host.files:
            console.print(host.files[fp])
        else:
            console.print_error(f"tar: {files[0]}: Cannot open: No such file or directory")
    elif "c" in flags and len(files) >= 2:
        # Create archive (simulated)
        archive = files[0] if files[0].startswith("/") else _resolve_path(host.cwd, files[0])
        source = files[1] if files[1].startswith("/") else _resolve_path(host.cwd, files[1])
        prefix = source.rstrip("/") + "/"
        contents = [f for f in host.files if f.startswith(prefix)]
        listing = "\n".join(contents)
        from commands.file_edit_cmds import _track_file
        _track_file(host, archive, f"[tar archive: {len(contents)} files]\n{listing}")
        console.print(f"[dim]tar: created {archive} ({len(contents)} files)[/dim]")
    elif "x" in flags and files:
        fp = files[0] if files[0].startswith("/") else _resolve_path(host.cwd, files[0])
        if fp in host.files:
            console.print(f"[dim]tar: extracted (simulated)[/dim]")
        else:
            console.print_error(f"tar: {files[0]}: Cannot open: No such file or directory")
    else:
        console.print_error("tar: need one of -c, -t, -x")


@register("zip", "cmd.zip.help", required_tool="zip")
def handle_zip(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: zip [OPTIONS] ARCHIVE FILES...\n  zip archive.zip file1 file2\n  zip -r archive.zip dir/")
        return
    if not _require_host(game): return
    non_flag = [a for a in args if not a.startswith("-")]
    if len(non_flag) < 2:
        console.print_error("zip: missing archive or file names")
        return
    archive = non_flag[0]
    files = non_flag[1:]
    host = game.current_host
    ap = archive if archive.startswith("/") else _resolve_path(host.cwd, archive)
    from commands.file_edit_cmds import _track_file
    _track_file(host, ap, f"[zip archive: {len(files)} entries]\n" + "\n".join(files))
    for f in files:
        console.print(f"  adding: {f}")
    console.print(f"[dim]zip: created {archive}[/dim]")


@register("unzip", "cmd.unzip.help", required_tool="unzip")
def handle_unzip(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: unzip [OPTIONS] ARCHIVE\n  unzip archive.zip\n  unzip -l archive.zip   list contents")
        return
    if not _require_host(game): return
    host = game.current_host
    fp = args[-1] if args[-1].startswith("/") else _resolve_path(host.cwd, args[-1])
    if fp not in host.files:
        console.print_error(f"unzip: cannot find {args[-1]}")
        return
    if "-l" in args:
        console.print(host.files[fp])
    else:
        console.print(f"[dim]unzip: extracted (simulated)[/dim]")


@register("gzip", "cmd.gzip.help", required_tool="gzip")
def handle_gzip(game, args):
    if _wants_help(args) or not args:
        console.print("Usage: gzip [OPTIONS] FILE...\n  gzip file       compress (creates file.gz)\n  gzip -d file.gz decompress\n  gzip -k file    keep original")
        return
    if not _require_host(game): return
    host = game.current_host
    decompress = "-d" in args
    keep = "-k" in args
    for a in args:
        if a.startswith("-"): continue
        fp = a if a.startswith("/") else _resolve_path(host.cwd, a)
        if fp not in host.files:
            console.print_error(f"gzip: {a}: No such file")
            continue
        if decompress:
            newname = fp.rstrip(".gz")
            host.files[newname] = host.files[fp]
            host.user_files[newname] = host.files[fp]
            if not keep:
                host.files.pop(fp, None)
                host.user_files[fp] = "__DELETED__"
        else:
            newname = fp + ".gz"
            host.files[newname] = f"[gzip compressed: {len(host.files[fp])} bytes]"
            host.user_files[newname] = host.files[newname]
            if not keep:
                host.files.pop(fp, None)
                host.user_files[fp] = "__DELETED__"


@register("gunzip", "cmd.gunzip.help", required_tool="gunzip")
def handle_gunzip(game, args):
    return handle_gzip(game, ["-d"] + list(args))


@register("diff", "cmd.diff.help", required_tool="diff")
def handle_diff(game, args):
    if _wants_help(args):
        console.print("Usage: diff [OPTIONS] FILE1 FILE2\n  diff file1 file2\n  diff -u file1 file2   unified format")
        return
    if not _require_host(game): return
    host = game.current_host
    files = [a for a in args if not a.startswith("-")]
    if len(files) < 2:
        console.print_error("diff: missing operand")
        return
    unified = "-u" in args
    f1 = files[0] if files[0].startswith("/") else _resolve_path(host.cwd, files[0])
    f2 = files[1] if files[1].startswith("/") else _resolve_path(host.cwd, files[1])
    for fp, name in [(f1, files[0]), (f2, files[1])]:
        if fp not in host.files:
            console.print_error(f"diff: {name}: No such file or directory")
            return
    lines1 = host.files[f1].split("\n")
    lines2 = host.files[f2].split("\n")
    if lines1 == lines2:
        return 0
    if unified:
        console.print(f"--- {files[0]}")
        console.print(f"+++ {files[1]}")
        console.print(f"@@ -1,{len(lines1)} +1,{len(lines2)} @@")
    for i, (a, b) in enumerate(zip(lines1, lines2)):
        if a != b:
            if unified:
                console.print(f"-{a}")
                console.print(f"+{b}")
            else:
                console.print(f"{i+1}c{i+1}")
                console.print(f"< {a}")
                console.print(f"---")
                console.print(f"> {b}")
    if len(lines1) > len(lines2):
        for line in lines1[len(lines2):]:
            console.print(f"-{line}" if unified else f"< {line}")
    elif len(lines2) > len(lines1):
        for line in lines2[len(lines1):]:
            console.print(f"+{line}" if unified else f"> {line}")
    return 1


@register("printf", "cmd.printf.help", required_tool="printf")
def handle_printf(game, args):
    if _wants_help(args) or not args:
        console.print('Usage: printf FORMAT [ARGUMENT]...\n  printf "%s\\n" hello\n  printf "%d\\n" 42\n  printf "%x\\n" 255')
        return
    fmt = args[0].replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
    fmt = fmt.replace("\\0", "\0").replace("\\\\", "\x01").replace("%%", "\x02")
    rest = list(args[1:])

    # Process format specifiers in order of appearance
    import re as _re
    spec_re = _re.compile(r'%[-+0 #]*(?:\d+)?(?:\.\d+)?[sdxXofecb%]')
    result = []
    val_idx = 0
    pos = 0
    for m in spec_re.finditer(fmt):
        result.append(fmt[pos:m.start()])
        spec = m.group()
        pos = m.end()
        if spec == "%%":
            result.append("%")
            continue
        val = rest[val_idx] if val_idx < len(rest) else ""
        val_idx += 1
        last_char = spec[-1]
        try:
            if last_char == 's':
                result.append(val)
            elif last_char == 'd':
                result.append(str(int(val)))
            elif last_char in ('x', 'X'):
                h = hex(int(val))[2:]
                result.append(h.upper() if last_char == 'X' else h)
            elif last_char == 'o':
                result.append(oct(int(val))[2:])
            elif last_char in ('f', 'e'):
                result.append(f"{float(val):.6f}" if last_char == 'f' else f"{float(val):e}")
            elif last_char == 'c':
                result.append(val[0] if val else "")
            elif last_char == 'b':
                result.append(val.replace("\\n", "\n").replace("\\t", "\t"))
            else:
                result.append(val)
        except (ValueError, IndexError):
            result.append(val if last_char == 's' else "0")
    result.append(fmt[pos:])
    output = "".join(result).replace("\x01", "\\").replace("\x02", "%")
    console.print(output, end="")


@register("column", "cmd.column.help", required_tool="column")
def handle_column(game, args):
    if _wants_help(args):
        console.print("Usage: column [OPTIONS] [FILE]\n  column -t          tabulate\n  column -t -s:      delimiter :")
        return
    if not _require_host(game): return
    content = _get_input(game, args, "column")
    if content is None: return
    tabulate = "-t" in args
    sep = None
    if "-s" in args:
        idx = args.index("-s")
        if idx + 1 < len(args): sep = args[idx + 1]
    for a in args:
        if a.startswith("-s") and len(a) > 2: sep = a[2:]

    lines = content.strip().split("\n")
    if tabulate:
        rows = [l.split(sep) if sep else l.split() for l in lines]
        if not rows: return
        max_cols = max(len(r) for r in rows)
        widths = [0] * max_cols
        for r in rows:
            for i, c in enumerate(r):
                if i < max_cols:
                    widths[i] = max(widths[i], len(c))
        for r in rows:
            parts = []
            for i, c in enumerate(r):
                if i < max_cols:
                    parts.append(c.ljust(widths[i]))
            console.print("  ".join(parts))
    else:
        console.print(content)


@register("od", "cmd.od.help", required_tool="od")
def handle_od(game, args):
    if _wants_help(args):
        console.print("Usage: od [OPTIONS] FILE\n  od -c file    character dump\n  od -x file    hex dump")
        return
    if not _require_host(game): return
    content = _get_input(game, args, "od")
    if content is None: return
    data = content.encode()[:256]
    char_mode = "-c" in args
    for offset in range(0, len(data), 16):
        chunk = data[offset:offset + 16]
        addr = f"{offset:07o}"
        if char_mode:
            parts = []
            for b in chunk:
                if b == ord('\n'): parts.append("\\n")
                elif b == ord('\t'): parts.append("\\t")
                elif b == ord(' '): parts.append("  ")
                elif 32 <= b < 127: parts.append(f" {chr(b)}")
                else: parts.append(f"\\{b:03o}")
            console.print(f"{addr} {'  '.join(parts)}")
        else:
            hex_parts = " ".join(f"{b:04x}" for b in chunk)
            console.print(f"{addr} {hex_parts}")


@register("nl", "cmd.nl.help", required_tool="nl")
def handle_nl(game, args):
    if _wants_help(args):
        console.print("Usage: nl [OPTIONS] [FILE]\n  nl file        number lines\n  nl -ba file    number ALL lines (including blank)")
        return
    if not _require_host(game): return
    content = _get_input(game, args, "nl")
    if content is None: return
    all_lines = "-ba" in args
    start = 1
    for a in args:
        if a.startswith("-v"):
            try: start = int(a[2:]) if len(a) > 2 else int(args[args.index(a)+1])
            except: pass
    n = start
    for line in content.split("\n"):
        if not line.strip() and not all_lines:
            console.print(f"{'':>6s}\t{line}")
        else:
            console.print(f"{n:>6d}\t{line}")
            n += 1
