from dataclasses import dataclass, field


@dataclass
class Player:
    handle: str = "hacker"
    reputation: int = 0
    tools_unlocked: list[str] = field(default_factory=lambda: [
        # Recon & access
        "nmap", "ping", "ssh", "exploit", "crack", "disconnect",
        # Filesystem
        "ls", "cd", "cat", "download", "head", "tail", "grep", "wc",
        "touch", "mkdir", "rm", "cp", "mv", "nano", "vi",
        # Linux standard
        "whoami", "pwd", "id", "uname", "hostname", "ifconfig", "ip",
        "ps", "env", "echo", "which", "date", "uptime", "free", "df",
        "mount", "netstat", "ss", "sudo", "su", "chmod", "man", "history",
        # Package management
        "apt",
        # Text processing
        "sort", "uniq", "cut", "tr", "sed", "awk", "tee", "xargs",
        "rev", "seq",
        # Network tools
        "wget", "nc", "netcat", "dig", "nslookup", "traceroute",
        "iptables", "scp", "whois",
        # CTF / forensics
        "strings", "xxd", "file", "base64", "md5sum", "sha256sum",
        "binwalk", "steghide", "exiftool", "curl",
        # Shell built-ins
        "export", "unset", "set", "alias", "unalias", "type",
        "exit", "sleep", "kill", "killall", "test", "[", "read",
        "find", "systemctl", "service", "dmesg", "journalctl",
        "source", "eval", "expr", "let", "timeout",
        "pgrep", "pkill", "host", "ssh-keygen", ".",
        # Sysadmin / utilities
        "stat", "du", "ln", "chown", "passwd", "useradd", "top",
        "lsblk", "lsof", "crontab", "tar", "zip", "unzip", "gzip",
        "gunzip", "diff", "printf", "column", "od", "nl",
        # Extra
        "true", "false", "basename", "dirname", "realpath", "rmdir",
        "readlink", "chgrp", "groupadd", "groupdel", "paste", "hexdump",
        "shred", "w", "who", "users", "last", "yes", "mktemp", "tac",
        "comm", "expand", "unexpand", "nohup", "reset",
        "bzip2", "bunzip2", "xz", "unxz",
        "usermod", "userdel", "getent",
        "jobs", "bg", "fg", "trap", "wait",
        "locate", "whereis",
        # System/Misc
        "cal", "bc", "watch", "lscpu", "lsusb", "lspci", "vmstat",
        "nice", "renice", "stty", "logger", "wall", "fold", "fmt", "screen", "tmux",
        "mkfifo", "truncate", "install", "split", "tput", "dc",
        "join", "htop", "chroot",
        "less", "more", "tree", "time", "dd", "umask", "ulimit",
        "sysctl", "ldd", "strace", "dpkg", "rsync", "cpio", "patch",
        "rename", "uuidgen", "xdg-open", "fuser", "iconv", "at",
        "apropos", "pv", "ar",
        "shutdown", "gpg", "locale", "pidof", "modprobe", "modinfo",
        "blkid", "fdisk", "finger", "timedatectl", "swapon", "nmcli",
        "runlevel",
        # Network/Security
        "telnet", "socat", "arp", "tcpdump", "ssh-agent", "ssh-add",
        "mtr", "openssl",
        # Development
        "git", "python3", "gcc", "make",
        # Game UI
        "help", "status", "missions", "clear", "quit", "hint",
    ])
    connected_to: str | None = None
    notes: list[str] = field(default_factory=list)
    completed_missions: list[str] = field(default_factory=list)
    files_read: set[str] = field(default_factory=set)
    files_downloaded: set[str] = field(default_factory=set)
    known_credentials: list[dict] = field(default_factory=list)

    def add_credential(self, username: str, password: str, host: str):
        cred = {"username": username, "password": password, "host": host}
        if cred not in self.known_credentials:
            self.known_credentials.append(cred)

    def has_credential_for(self, host_ip: str, username: str = "") -> dict | None:
        for cred in self.known_credentials:
            if cred["host"] == host_ip:
                if not username or cred["username"] == username:
                    return cred
        return None
