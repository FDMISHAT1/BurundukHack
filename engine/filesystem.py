"""
Generates a realistic Linux filesystem for simulated hosts.
The YAML only defines custom/mission-specific files — this module
auto-generates everything else (etc, proc, var, home, usr, …).
"""
import random
import hashlib

# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def generate_linux_fs(hostname: str, ip: str, os_name: str,
                      users: list[dict], services: list,
                      custom_files: dict[str, str] | None = None):
    """Return (files, file_meta) for a complete Linux host."""
    files: dict[str, str] = {}
    meta: dict[str, dict] = {}

    os_type = _detect_os_type(os_name)

    _add_base_dirs(files, meta)
    _add_etc(files, meta, hostname, ip, os_name, os_type, users, services)
    _add_proc(files, meta, os_name, hostname)
    _add_home(files, meta, users, hostname)
    _add_root_dir(files, meta, hostname)
    _add_var(files, meta, hostname, ip, services, users)
    _add_usr_bin(files, meta)
    _add_tmp(files, meta)
    _add_boot(files, meta, os_name)
    _add_dev(files, meta)
    _add_service_files(files, meta, services, hostname, ip, users, os_type)

    # Overlay custom (mission) files on top
    if custom_files:
        for path, content in custom_files.items():
            files[path] = content
            if path not in meta:
                meta[path] = _default_meta(path, users)

    return files, meta


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _detect_os_type(os_name: str) -> str:
    low = os_name.lower()
    if "ubuntu" in low or "debian" in low or "kali" in low:
        return "debian"
    if "centos" in low or "rhel" in low or "red hat" in low or "fedora" in low:
        return "rhel"
    if "cisco" in low:
        return "cisco"
    return "debian"  # default


def _default_meta(path: str, users: list[dict] | None = None) -> dict:
    """Guess reasonable metadata from the path."""
    user_names = [u.get("name", "user") for u in (users or [])]
    parts = path.strip("/").split("/")

    owner = "root"
    group = "root"
    perms = "-rw-r--r--"
    mtime = _rand_date()

    if parts[0] == "home" and len(parts) > 1:
        u = parts[1]
        owner = u
        group = u
        if u in user_names:
            perms = "-rw-r--r--"
    elif parts[0] == "root":
        perms = "-rw-------"
    elif parts[0] == "etc" and "shadow" in path:
        perms = "-rw-r-----"
        group = "shadow"
    elif parts[0] in ("bin", "sbin", "usr"):
        perms = "-rwxr-xr-x"
    elif parts[0] == "var" and "log" in path:
        group = "adm"
        perms = "-rw-r-----"
    elif parts[0] == "tmp":
        perms = "-rw-rw-rw-"

    return {"perms": perms, "owner": owner, "group": group, "mtime": mtime}


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _rand_date(year_range=(2024, 2025)) -> str:
    m = random.choice(_MONTHS)
    d = random.randint(1, 28)
    h = random.randint(0, 23)
    mi = random.randint(0, 59)
    return f"{m} {d:2d} {h:02d}:{mi:02d}"


def _stable_date(seed: str) -> str:
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    m = _MONTHS[h % 12]
    d = (h >> 4) % 28 + 1
    hr = (h >> 8) % 24
    mi = (h >> 12) % 60
    return f"{m} {d:2d} {hr:02d}:{mi:02d}"


def _fake_hash(username: str) -> str:
    h = hashlib.sha256(username.encode()).hexdigest()[:60]
    return f"$6${h[:8]}${h[8:]}"


def _add(files, meta, path, content, perms="-rw-r--r--",
         owner="root", group="root", mtime=None):
    files[path] = content
    meta[path] = {
        "perms": perms, "owner": owner, "group": group,
        "mtime": mtime or _stable_date(path),
    }


# ---------------------------------------------------------------------------
#  /  base directories (markers)
# ---------------------------------------------------------------------------

def _add_base_dirs(files, meta):
    pass  # Directories are implicit from files in them


# ---------------------------------------------------------------------------
#  /etc
# ---------------------------------------------------------------------------

def _add_etc(files, meta, hostname, ip, os_name, os_type, users, services):
    # --- /etc/hostname ---
    _add(files, meta, "/etc/hostname", hostname)

    # --- /etc/hosts ---
    hosts_content = f"""127.0.0.1\tlocalhost
127.0.1.1\t{hostname}
{ip}\t{hostname}

# The following lines are desirable for IPv6 capable hosts
::1\t\tip6-localhost ip6-loopback
fe00::0\t\tip6-localnet
ff00::0\t\tip6-mcastprefix
ff02::1\t\tip6-allnodes
ff02::2\t\tip6-allrouters"""
    _add(files, meta, "/etc/hosts", hosts_content)

    # --- /etc/resolv.conf ---
    _add(files, meta, "/etc/resolv.conf",
         "nameserver 8.8.8.8\nnameserver 8.8.4.4\nsearch localdomain\n")

    # --- /etc/os-release ---
    if "kali" in os_name.lower():
        _add(files, meta, "/etc/os-release", f"""NAME="Kali GNU/Linux"
VERSION="2024.3"
ID=kali
ID_LIKE=debian
PRETTY_NAME="{os_name}"
VERSION_ID="2024.3"
HOME_URL="https://www.kali.org/"
SUPPORT_URL="https://forums.kali.org/"
BUG_REPORT_URL="https://bugs.kali.org/"
ANSI_COLOR="1;31" """)
        _add(files, meta, "/etc/issue", "Kali GNU/Linux Rolling \\n \\l\n")
    elif os_type == "debian":
        ver = "20.04" if "20.04" in os_name else "22.04"
        code = "focal" if ver == "20.04" else "jammy"
        _add(files, meta, "/etc/os-release", f"""NAME="Ubuntu"
VERSION="{ver} LTS ({code.title()} Fossa)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu {ver} LTS"
VERSION_ID="{ver}"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
VERSION_CODENAME={code}
UBUNTU_CODENAME={code}""")
    elif os_type == "rhel":
        _add(files, meta, "/etc/os-release", f"""NAME="CentOS Linux"
VERSION="7 (Core)"
ID="centos"
ID_LIKE="rhel fedora"
VERSION_ID="7"
PRETTY_NAME="{os_name}"
CPE_NAME="cpe:/o:centos:centos:7"
HOME_URL="https://www.centos.org/"
BUG_REPORT_URL="https://bugs.centos.org/"
CENTOS_MANTISBT_PROJECT="CentOS-7"
CENTOS_MANTISBT_PROJECT_VERSION="7" """)

    # --- /etc/issue (skip if already set by Kali block above) ---
    if "/etc/issue" not in files:
        if os_type == "debian":
            _add(files, meta, "/etc/issue", f"Ubuntu {ver} \\n \\l\n")
        else:
            _add(files, meta, "/etc/issue",
                 f"CentOS Linux 7 (Core)\nKernel 3.10.0-1160.el7.x86_64 on an x86_64\n")

    # --- /etc/motd ---
    _add(files, meta, "/etc/motd", "")

    # --- /etc/passwd ---
    passwd_lines = [
        "root:x:0:0:root:/root:/bin/bash",
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
        "bin:x:2:2:bin:/bin:/usr/sbin/nologin",
        "sys:x:3:3:sys:/dev:/usr/sbin/nologin",
        "sync:x:4:65534:sync:/bin:/bin/sync",
        "games:x:5:60:games:/usr/games:/usr/sbin/nologin",
        "man:x:6:12:man:/var/cache/man:/usr/sbin/nologin",
        "lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin",
        "mail:x:8:8:mail:/var/mail:/usr/sbin/nologin",
        "news:x:9:9:news:/var/spool/news:/usr/sbin/nologin",
        "uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin",
        "proxy:x:13:13:proxy:/bin:/usr/sbin/nologin",
        "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin",
        "backup:x:34:34:backup:/var/backups:/usr/sbin/nologin",
        "list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin",
        "irc:x:39:39:ircd:/run/ircd:/usr/sbin/nologin",
        "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin",
        "systemd-network:x:100:102:systemd Network Management,,,:/run/systemd:/usr/sbin/nologin",
        "syslog:x:104:110::/home/syslog:/usr/sbin/nologin",
        "sshd:x:105:65534::/run/sshd:/usr/sbin/nologin",
    ]
    uid = 1000
    for u in users:
        name = u.get("name", "user")
        role = u.get("role", "")
        passwd_lines.append(
            f"{name}:x:{uid}:{uid}:{role}:/home/{name}:/bin/bash"
        )
        uid += 1
    _add(files, meta, "/etc/passwd", "\n".join(passwd_lines) + "\n")

    # --- /etc/shadow ---
    shadow_lines = [
        f"root:{_fake_hash('root')}:19500:0:99999:7:::",
        "daemon:*:18858:0:99999:7:::",
        "bin:*:18858:0:99999:7:::",
        "sys:*:18858:0:99999:7:::",
        "sync:*:18858:0:99999:7:::",
        "nobody:*:18858:0:99999:7:::",
        "sshd:*:18858:0:99999:7:::",
    ]
    for u in users:
        name = u.get("name", "user")
        shadow_lines.append(f"{name}:{_fake_hash(name)}:19500:0:99999:7:::")
    _add(files, meta, "/etc/shadow", "\n".join(shadow_lines) + "\n",
         perms="-rw-r-----", group="shadow")

    # --- /etc/group ---
    group_lines = [
        "root:x:0:",
        "daemon:x:1:",
        "bin:x:2:",
        "sys:x:3:",
        "adm:x:4:syslog",
        "tty:x:5:",
        "disk:x:6:",
        "lp:x:7:",
        "mail:x:8:",
        "news:x:9:",
        "www-data:x:33:",
        "shadow:x:42:",
        "sudo:x:27:" + ",".join(u.get("name", "") for u in users),
        "nogroup:x:65534:",
        "sshd:x:65534:",
    ]
    gid = 1000
    for u in users:
        name = u.get("name", "user")
        group_lines.append(f"{name}:x:{gid}:")
        gid += 1
    _add(files, meta, "/etc/group", "\n".join(group_lines) + "\n")

    # --- /etc/fstab ---
    uuid1 = hashlib.md5(f"{hostname}-root".encode()).hexdigest()[:8]
    uuid2 = hashlib.md5(f"{hostname}-swap".encode()).hexdigest()[:8]
    _add(files, meta, "/etc/fstab", f"""# /etc/fstab: static file system information.
#
# <file system>                           <mount point>  <type>  <options>        <dump>  <pass>
UUID={uuid1}-{uuid1}-{uuid1}-{uuid1}-{uuid1}00000  /              ext4    errors=remount-ro 0       1
UUID={uuid2}-{uuid2}-{uuid2}-{uuid2}-{uuid2}00000  none           swap    sw                0       0
tmpfs                                     /tmp           tmpfs   defaults          0       0""")

    # --- /etc/sudoers ---
    sudoers = """# /etc/sudoers
#
# This file MUST be edited with 'visudo' as root.
Defaults\tenv_reset
Defaults\tmail_badpass
Defaults\tsecure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Host alias specification
# User alias specification
# Cmnd alias specification

# User privilege specification
root\tALL=(ALL:ALL) ALL

# Members of the admin group may gain root privileges
%admin ALL=(ALL) ALL

# Allow members of group sudo to execute any command
%sudo\tALL=(ALL:ALL) ALL
"""
    _add(files, meta, "/etc/sudoers", sudoers, perms="-r--r-----")

    # --- /etc/ssh/sshd_config ---
    _add(files, meta, "/etc/ssh/sshd_config", f"""# OpenSSH Server configuration
Port 22
AddressFamily any
ListenAddress 0.0.0.0
ListenAddress ::

HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key

# Logging
SyslogFacility AUTH
LogLevel INFO

# Authentication
LoginGraceTime 2m
PermitRootLogin prohibit-password
StrictModes yes
MaxAuthTries 6
MaxSessions 10
PubkeyAuthentication yes
PasswordAuthentication yes
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding yes
PrintMotd no
AcceptEnv LANG LC_*
Subsystem\tsftp\t/usr/lib/openssh/sftp-server""")

    # --- /etc/crontab ---
    _add(files, meta, "/etc/crontab", f"""# /etc/crontab: system-wide crontab
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# m h dom mon dow user  command
17 *\t* * *\troot\tcd / && run-parts --report /etc/cron.hourly
25 6\t* * *\troot\ttest -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.daily )
47 6\t* * 7\troot\ttest -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.weekly )
52 6\t1 * *\troot\ttest -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.monthly )""")

    # --- /etc/network/interfaces ---
    _add(files, meta, "/etc/network/interfaces", f"""# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto eth0
iface eth0 inet static
\taddress {ip}
\tnetmask 255.255.255.0
\tgateway {ip.rsplit('.', 1)[0]}.1
\tdns-nameservers 8.8.8.8 8.8.4.4""")

    # --- /etc/apt/sources.list (debian-based) ---
    if "kali" in os_name.lower():
        _add(files, meta, "/etc/apt/sources.list",
             "# See https://www.kali.org/docs/general-use/kali-linux-sources-list-repositories/\n"
             "deb http://http.kali.org/kali kali-rolling main contrib non-free non-free-firmware\n"
             "# deb-src http://http.kali.org/kali kali-rolling main contrib non-free non-free-firmware\n")
    elif os_type == "debian":
        code = "focal" if "20.04" in os_name else "jammy"
        _add(files, meta, "/etc/apt/sources.list", f"""# See http://help.ubuntu.com/community/UpgradeNotes for how to upgrade to
# newer versions of the distribution.
deb http://archive.ubuntu.com/ubuntu/ {code} main restricted
deb http://archive.ubuntu.com/ubuntu/ {code}-updates main restricted
deb http://archive.ubuntu.com/ubuntu/ {code} universe
deb http://archive.ubuntu.com/ubuntu/ {code}-updates universe
deb http://archive.ubuntu.com/ubuntu/ {code} multiverse
deb http://archive.ubuntu.com/ubuntu/ {code}-updates multiverse
deb http://security.ubuntu.com/ubuntu {code}-security main restricted
deb http://security.ubuntu.com/ubuntu {code}-security universe
deb http://security.ubuntu.com/ubuntu {code}-security multiverse""")
    elif os_type == "rhel":
        _add(files, meta, "/etc/yum.repos.d/CentOS-Base.repo", """[base]
name=CentOS-7 - Base
mirrorlist=http://mirrorlist.centos.org/?release=7&arch=$basearch&repo=os
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7

[updates]
name=CentOS-7 - Updates
mirrorlist=http://mirrorlist.centos.org/?release=7&arch=$basearch&repo=updates
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7""")

    # --- /etc/environment ---
    _add(files, meta, "/etc/environment",
         'PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n')

    # --- /etc/locale.gen ---
    _add(files, meta, "/etc/default/locale", "LANG=en_US.UTF-8\n")

    # --- /etc/timezone ---
    _add(files, meta, "/etc/timezone", "Etc/UTC\n")

    # --- /etc/localtime (binary marker) ---
    _add(files, meta, "/etc/machine-id",
         hashlib.md5(hostname.encode()).hexdigest() + "\n")


# ---------------------------------------------------------------------------
#  /proc
# ---------------------------------------------------------------------------

def _add_proc(files, meta, os_name, hostname):
    kernel = "5.4.0-42-generic" if "20" in os_name else "5.15.0-91-generic"
    gcc = "9.3.0" if "20" in os_name else "11.4.0"

    _add(files, meta, "/proc/version",
         f"Linux version {kernel} (buildd@lgw01-amd64-038) "
         f"(gcc version {gcc} (Ubuntu {gcc}-17ubuntu1)) "
         f"#46-Ubuntu SMP Fri Jul 10 00:24:02 UTC 2024\n",
         perms="-r--r--r--")

    _add(files, meta, "/proc/cpuinfo", """processor\t: 0
vendor_id\t: GenuineIntel
cpu family\t: 6
model\t\t: 142
model name\t: Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz
stepping\t: 10
microcode\t: 0xf0
cpu MHz\t\t: 1800.000
cache size\t: 6144 KB
physical id\t: 0
siblings\t: 4
core id\t\t: 0
cpu cores\t: 4
apicid\t\t: 0
fpu\t\t: yes
fpu_exception\t: yes
cpuid level\t: 22
wp\t\t: yes
flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss ht syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl xtopology
bogomips\t: 3600.00
clflush size\t: 64
cache_alignment\t: 64
address sizes\t: 39 bits physical, 48 bits virtual

processor\t: 1
vendor_id\t: GenuineIntel
cpu family\t: 6
model\t\t: 142
model name\t: Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz
stepping\t: 10
cpu MHz\t\t: 1800.000
cache size\t: 6144 KB
physical id\t: 0
siblings\t: 4
core id\t\t: 1
cpu cores\t: 4
bogomips\t: 3600.00
""", perms="-r--r--r--")

    mem_total = random.randint(4000000, 16000000)
    mem_free = random.randint(mem_total // 4, mem_total // 2)
    mem_avail = mem_free + random.randint(500000, 2000000)
    _add(files, meta, "/proc/meminfo", f"""MemTotal:       {mem_total} kB
MemFree:        {mem_free} kB
MemAvailable:   {mem_avail} kB
Buffers:         {random.randint(50000, 200000)} kB
Cached:         {random.randint(500000, 3000000)} kB
SwapCached:            0 kB
Active:         {random.randint(1000000, 4000000)} kB
Inactive:       {random.randint(500000, 2000000)} kB
SwapTotal:      {mem_total // 2} kB
SwapFree:       {mem_total // 2} kB
Dirty:                 0 kB
Writeback:             0 kB
""", perms="-r--r--r--")

    _add(files, meta, "/proc/uptime", f"{random.randint(10000, 999999)}.{random.randint(10,99)} {random.randint(10000, 999999)}.{random.randint(10,99)}\n",
         perms="-r--r--r--")

    _add(files, meta, "/proc/loadavg",
         f"0.{random.randint(0,99):02d} 0.{random.randint(0,99):02d} 0.{random.randint(0,99):02d} 1/{random.randint(100,300)} {random.randint(1000,9999)}\n",
         perms="-r--r--r--")

    _add(files, meta, "/proc/sys/kernel/hostname", hostname + "\n",
         perms="-r--r--r--")


# ---------------------------------------------------------------------------
#  /home/*
# ---------------------------------------------------------------------------

def _add_home(files, meta, users, hostname):
    for u in users:
        name = u.get("name", "user")
        home = f"/home/{name}"

        _add(files, meta, f"{home}/.bashrc", f"""# ~/.bashrc: executed by bash(1) for non-login shells.

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=1000
HISTFILESIZE=2000
shopt -s checkwinsize

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set a fancy prompt (non-color, unless we know we "want" color)
PS1='${{debian_chroot:+($debian_chroot)}}\\u@\\h:\\w\\$ '

# enable color support of ls
alias ls='ls --color=auto'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias grep='grep --color=auto'
""", owner=name, group=name)

        _add(files, meta, f"{home}/.profile", """# ~/.profile: executed by the command interpreter for login shells.

# if running bash
if [ -n "$BASH_VERSION" ]; then
    if [ -f "$HOME/.bashrc" ]; then
        . "$HOME/.bashrc"
    fi
fi

# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/bin" ] ; then
    PATH="$HOME/bin:$PATH"
fi

if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi
""", owner=name, group=name)

        _add(files, meta, f"{home}/.bash_logout",
             "# ~/.bash_logout: executed by bash(1) when login shell exits.\n\n"
             "# when leaving the console clear the screen to increase privacy\nif [ \"$SHLVL\" = 1 ]; then\n"
             "    [ -x /usr/bin/clear_console ] && /usr/bin/clear_console -q\nfi\n",
             owner=name, group=name)

        _add(files, meta, f"{home}/.sudo_as_admin_successful", "",
             owner=name, group=name)

        email = u.get("email", f"{name}@{hostname}")
        _add(files, meta, f"{home}/.gitconfig",
             f"[user]\n\tname = {name}\n\temail = {email}\n",
             owner=name, group=name)


# ---------------------------------------------------------------------------
#  /root
# ---------------------------------------------------------------------------

def _add_root_dir(files, meta, hostname):
    _add(files, meta, "/root/.bashrc", """# ~/.bashrc: executed by bash(1) for non-login shells.

export HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=1000
HISTFILESIZE=2000

PS1='${debian_chroot:+(${debian_chroot})}\\[\\033[01;31m\\]\\u@\\h\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\# '

alias ls='ls --color=auto'
alias ll='ls -alF'
alias grep='grep --color=auto'

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
""", perms="-rw-------")

    _add(files, meta, "/root/.profile",
         "# ~/.profile: executed by Bourne-compatible login shells.\n\n"
         "if [ \"$BASH\" ]; then\n  if [ -f ~/.bashrc ]; then\n    . ~/.bashrc\n  fi\nfi\n\n"
         "mesg n 2>/dev/null || true\n",
         perms="-rw-------")


# ---------------------------------------------------------------------------
#  /var
# ---------------------------------------------------------------------------

def _add_var(files, meta, hostname, ip, services, users):
    subnet_base = ip.rsplit(".", 1)[0]

    # --- /var/log/auth.log ---
    auth_lines = []
    for u in users:
        name = u.get("name", "user")
        src_ip = f"{subnet_base}.{random.randint(2, 254)}"
        port = random.randint(40000, 65000)
        auth_lines.append(
            f"Nov 14 09:15:23 {hostname} sshd[{random.randint(1000,9999)}]: "
            f"Accepted password for {name} from {src_ip} port {port} ssh2"
        )
    auth_lines.append(
        f"Nov 15 14:32:01 {hostname} sshd[{random.randint(1000,9999)}]: "
        f"Server listening on 0.0.0.0 port 22."
    )
    auth_lines.append(
        f"Nov 15 14:32:01 {hostname} sshd[{random.randint(1000,9999)}]: "
        f"Server listening on :: port 22."
    )
    _add(files, meta, "/var/log/auth.log", "\n".join(auth_lines) + "\n",
         perms="-rw-r-----", group="adm")

    # --- /var/log/syslog ---
    syslog_lines = [
        f"Nov 15 14:30:01 {hostname} CRON[{random.randint(1000,9999)}]: (root) CMD (   /usr/sbin/ntpdate -u ntp.ubuntu.com)",
        f"Nov 15 14:30:01 {hostname} systemd[1]: Started System Logging Service.",
        f"Nov 15 14:30:02 {hostname} systemd[1]: Started OpenBSD Secure Shell server.",
        f"Nov 15 14:30:02 {hostname} kernel: [    0.000000] Linux version 5.4.0-42-generic",
        f"Nov 15 14:30:02 {hostname} kernel: [    0.000000] Command line: BOOT_IMAGE=/vmlinuz-5.4.0-42-generic root=UUID=a1b2c3d4",
        f"Nov 15 14:30:02 {hostname} systemd[1]: Reached target Network is Online.",
        f"Nov 15 14:31:01 {hostname} CRON[{random.randint(1000,9999)}]: (root) CMD (   cd / && run-parts --report /etc/cron.hourly)",
    ]
    for svc in services:
        svc_name = svc.name if hasattr(svc, 'name') else svc.get('name', 'unknown')
        syslog_lines.append(
            f"Nov 15 14:30:03 {hostname} systemd[1]: Started {svc_name} service."
        )
    _add(files, meta, "/var/log/syslog", "\n".join(syslog_lines) + "\n",
         perms="-rw-r-----", group="adm")

    # --- /var/log/dpkg.log ---
    _add(files, meta, "/var/log/dpkg.log",
         "2024-11-10 10:00:01 startup packages configure\n"
         "2024-11-10 10:00:02 configure openssh-server:amd64 1:8.2p1-4ubuntu0.9 <none>\n"
         "2024-11-10 10:00:03 status installed openssh-server:amd64 1:8.2p1-4ubuntu0.9\n",
         perms="-rw-r--r--")

    # --- /var/log/lastlog (binary) ---
    _add(files, meta, "/var/log/lastlog", "[binary: lastlog data]",
         perms="-rw-rw-r--", group="utmp")

    # --- /var/log/wtmp (binary) ---
    _add(files, meta, "/var/log/wtmp", "[binary: wtmp data]",
         perms="-rw-rw-r--", group="utmp")

    # --- /var/mail (empty marker) ---
    _add(files, meta, "/var/mail/.keep", "")

    # --- /var/tmp ---
    _add(files, meta, "/var/tmp/.keep", "", perms="-rw-rw-rw-")

    # --- /var/lib/dpkg/status (partial) ---
    _add(files, meta, "/var/lib/dpkg/status",
         "Package: bash\nStatus: install ok installed\nPriority: required\n"
         "Section: shells\nInstalled-Size: 1768\nVersion: 5.0-6ubuntu1.2\n"
         "Architecture: amd64\nDescription: GNU Bourne Again SHell\n\n"
         "Package: openssh-server\nStatus: install ok installed\nPriority: optional\n"
         "Section: net\nInstalled-Size: 920\nVersion: 1:8.2p1-4ubuntu0.9\n"
         "Architecture: amd64\nDescription: secure shell (SSH) server\n\n")


# ---------------------------------------------------------------------------
#  /usr/bin
# ---------------------------------------------------------------------------

_COMMON_BINS = [
    "bash", "sh", "dash", "cat", "ls", "cp", "mv", "rm", "mkdir", "rmdir",
    "chmod", "chown", "chgrp", "ln", "touch", "date", "echo", "env",
    "false", "true", "pwd", "sleep", "test", "wc", "head", "tail",
    "sort", "uniq", "cut", "tr", "tee", "xargs", "find", "grep", "egrep",
    "sed", "awk", "diff", "tar", "gzip", "gunzip", "bzip2", "zip", "unzip",
    "less", "more", "vi", "nano", "clear", "reset", "tput",
    "whoami", "id", "groups", "users", "w", "who", "last", "lastlog",
    "su", "sudo", "passwd", "useradd", "userdel", "usermod",
    "hostname", "uname", "uptime", "free", "df", "du", "mount", "umount",
    "ps", "top", "htop", "kill", "killall", "nice", "renice",
    "ifconfig", "ip", "ping", "traceroute", "netstat", "ss", "nslookup",
    "dig", "host", "wget", "curl", "ssh", "scp", "sftp",
    "apt", "apt-get", "dpkg", "snap",
    "systemctl", "service", "journalctl",
    "crontab", "at",
    "man", "info", "whatis", "which", "whereis", "file", "stat",
    "md5sum", "sha256sum", "base64",
    "git", "python3", "perl", "php",
]


def _add_usr_bin(files, meta):
    for cmd in _COMMON_BINS:
        _add(files, meta, f"/usr/bin/{cmd}",
             f"[ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked]",
             perms="-rwxr-xr-x")
    # sbin
    for cmd in ["iptables", "ip6tables", "fdisk", "mkfs", "fsck", "reboot",
                "shutdown", "halt", "init", "sshd", "cron", "rsyslogd",
                "nginx", "apache2", "mysqld"]:
        _add(files, meta, f"/usr/sbin/{cmd}",
             f"[ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked]",
             perms="-rwxr-xr-x")


# ---------------------------------------------------------------------------
#  /tmp
# ---------------------------------------------------------------------------

def _add_tmp(files, meta):
    _add(files, meta, "/tmp/.X11-unix/.keep", "", perms="-rw-rw-rw-")
    _add(files, meta, "/tmp/systemd-private/.keep", "", perms="-rw-------")


# ---------------------------------------------------------------------------
#  /boot
# ---------------------------------------------------------------------------

def _add_boot(files, meta, os_name):
    kernel = "5.4.0-42-generic" if "20" in os_name else "5.15.0-91-generic"
    _add(files, meta, f"/boot/vmlinuz-{kernel}",
         "[binary: Linux kernel x86 boot executable]",
         perms="-rw-------")
    _add(files, meta, f"/boot/initrd.img-{kernel}",
         "[binary: gzip compressed data]",
         perms="-rw-------")
    _add(files, meta, "/boot/grub/grub.cfg",
         f"# GRUB configuration\nset default=0\nset timeout=5\n"
         f"menuentry 'Ubuntu, with Linux {kernel}' {{\n"
         f"  linux /vmlinuz-{kernel} root=UUID=a1b2c3d4 ro quiet splash\n"
         f"  initrd /initrd.img-{kernel}\n}}\n",
         perms="-r--r--r--")


# ---------------------------------------------------------------------------
#  /dev
# ---------------------------------------------------------------------------

def _add_dev(files, meta):
    devs = {
        "/dev/null": "crw-rw-rw-",
        "/dev/zero": "crw-rw-rw-",
        "/dev/random": "crw-rw-rw-",
        "/dev/urandom": "crw-rw-rw-",
        "/dev/tty": "crw-rw-rw-",
        "/dev/console": "crw-------",
        "/dev/sda": "brw-rw----",
        "/dev/sda1": "brw-rw----",
        "/dev/sda2": "brw-rw----",
    }
    for path, perms in devs.items():
        _add(files, meta, path, "[device node]", perms=perms, group="disk")


# ---------------------------------------------------------------------------
#  Service-specific files
# ---------------------------------------------------------------------------

def _add_service_files(files, meta, services, hostname, ip, users, os_type):
    for svc in services:
        name = svc.name if hasattr(svc, "name") else svc.get("name", "")

        if name in ("http", "apache"):
            _add(files, meta, "/etc/apache2/apache2.conf",
                 f"# Apache2 configuration\nServerRoot \"/etc/apache2\"\n"
                 f"Timeout 300\nKeepAlive On\nMaxKeepAliveRequests 100\n"
                 f"HostnameLookups Off\nErrorLog ${{APACHE_LOG_DIR}}/error.log\n"
                 f"LogLevel warn\n")
            _add(files, meta, "/etc/apache2/sites-enabled/000-default.conf",
                 f"<VirtualHost *:80>\n\tServerAdmin webmaster@{hostname}\n"
                 f"\tDocumentRoot /var/www/html\n\tErrorLog ${{APACHE_LOG_DIR}}/error.log\n"
                 f"\tCustomLog ${{APACHE_LOG_DIR}}/access.log combined\n</VirtualHost>\n")
            _add(files, meta, "/var/www/html/index.html",
                 f"<!DOCTYPE html>\n<html><head><title>{hostname}</title></head>\n"
                 f"<body><h1>It works!</h1>\n<p>This is the default web page for {hostname}.</p>"
                 f"\n</body></html>\n",
                 owner="www-data", group="www-data")
            _add(files, meta, "/var/log/apache2/access.log",
                 f'{ip.rsplit(".", 1)[0]}.50 - - [15/Nov/2024:14:32:01 +0000] '
                 f'"GET / HTTP/1.1" 200 3380 "-" "Mozilla/5.0"\n',
                 perms="-rw-r-----", group="adm")
            _add(files, meta, "/var/log/apache2/error.log",
                 f"[Fri Nov 15 14:30:02.000000 2024] [mpm_prefork:notice] "
                 f"[pid 1234] AH00163: Apache/2.4.41 (Ubuntu) configured -- resuming normal operations\n",
                 perms="-rw-r-----", group="adm")

        elif name == "mysql":
            port_val = svc.port if hasattr(svc, "port") else svc.get("port", 3306)
            _add(files, meta, "/etc/mysql/my.cnf",
                 f"[mysqld]\nbind-address = 0.0.0.0\nport = {port_val}\n"
                 f"datadir = /var/lib/mysql\nsocket = /var/run/mysqld/mysqld.sock\n"
                 f"log_error = /var/log/mysql/error.log\npid-file = /var/run/mysqld/mysqld.pid\n"
                 f"\n# Performance\nmax_connections = 151\ninnodb_buffer_pool_size = 128M\n")
            _add(files, meta, "/var/log/mysql/error.log",
                 f"2024-11-15T14:30:01.000000Z 0 [System] [MY-010116] /usr/sbin/mysqld (mysqld 5.7.31) starting\n"
                 f"2024-11-15T14:30:02.000000Z 0 [System] [MY-010931] /usr/sbin/mysqld: ready for connections.\n"
                 f"Version: '5.7.31'  socket: '/var/run/mysqld/mysqld.sock'  port: {port_val}\n",
                 perms="-rw-r-----", group="adm")

        elif name == "nginx":
            _add(files, meta, "/etc/nginx/nginx.conf",
                 f"user www-data;\nworker_processes auto;\npid /run/nginx.pid;\n\n"
                 f"events {{\n\tworker_connections 768;\n}}\n\n"
                 f"http {{\n\tsendfile on;\n\ttcp_nopush on;\n\tinclude /etc/nginx/mime.types;\n"
                 f"\tdefault_type application/octet-stream;\n\taccess_log /var/log/nginx/access.log;\n"
                 f"\terror_log /var/log/nginx/error.log;\n\tinclude /etc/nginx/conf.d/*.conf;\n"
                 f"\tinclude /etc/nginx/sites-enabled/*;\n}}\n")

        elif name == "ftp":
            _add(files, meta, "/etc/vsftpd.conf",
                 "listen=YES\nlocal_enable=YES\nwrite_enable=YES\n"
                 "anonymous_enable=NO\ndirmessage_enable=YES\n"
                 "use_localtime=YES\nxferlog_enable=YES\nsecure_chroot_dir=/var/run/vsftpd/empty\n"
                 "pam_service_name=vsftpd\nrsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem\n")


# ---------------------------------------------------------------------------
#  MOTD generator (for SSH connection)
# ---------------------------------------------------------------------------

def generate_motd(hostname: str, ip: str, os_name: str, users: list[dict]) -> str:
    """Generate a realistic SSH login banner."""
    os_type = _detect_os_type(os_name)

    if os_type == "debian":
        ver = "20.04.6" if "20.04" in os_name else "22.04.3"
        kernel = "5.4.0-42-generic" if "20" in os_name else "5.15.0-91-generic"
        return f"""Welcome to Ubuntu {ver} LTS (GNU/Linux {kernel} x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

  System information as of Fri Nov 15 14:32:01 UTC 2024

  System load:  0.{random.randint(1,99):02d}             Processes:             {random.randint(80,250)}
  Usage of /:   {random.randint(20,75)}.{random.randint(0,9)}% of 19.56GB   Users logged in:       {len(users)}
  Memory usage: {random.randint(15,75)}%               IPv4 address for eth0: {ip}
  Swap usage:   0%

{random.randint(0, 20)} updates can be applied immediately.
{random.randint(0, 5)} of these updates are security updates.

Last login: Thu Nov 14 09:15:23 2024 from {ip.rsplit('.', 1)[0]}.{random.randint(2, 254)}
"""
    elif os_type == "rhel":
        return f"""CentOS Linux 7 (Core)
Kernel 3.10.0-1160.el7.x86_64 on an x86_64

Last login: Thu Nov 14 09:15:23 from {ip.rsplit('.', 1)[0]}.{random.randint(2,254)}
"""
    return f"Welcome to {hostname}\n"
