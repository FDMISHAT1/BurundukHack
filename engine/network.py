from dataclasses import dataclass, field
from pathlib import Path
import yaml

from engine.filesystem import generate_linux_fs


@dataclass
class Service:
    name: str
    port: int
    version: str
    vulnerable: bool = False
    exploit_name: str = ""
    credentials: dict = field(default_factory=dict)


@dataclass
class Host:
    ip: str
    hostname: str
    os: str
    services: list[Service] = field(default_factory=list)
    firewall_level: int = 0
    compromised: bool = False
    access_level: str = "none"  # "none", "user", "root"
    files: dict[str, str] = field(default_factory=dict)
    file_meta: dict[str, dict] = field(default_factory=dict)
    users: list[dict] = field(default_factory=list)
    cwd: str = "/"
    installed_packages: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    user_files: dict[str, str] = field(default_factory=dict)  # tracks user-created/modified files for saving

    def get_service_by_port(self, port: int) -> Service | None:
        for svc in self.services:
            if svc.port == port:
                return svc
        return None

    def get_service_by_name(self, name: str) -> Service | None:
        for svc in self.services:
            if svc.name == name:
                return svc
        return None

    def get_vulnerable_services(self) -> list[Service]:
        return [s for s in self.services if s.vulnerable]

    def get_current_user(self) -> str:
        if self.access_level == "root":
            return "root"
        if self.users:
            return self.users[0].get("name", "user")
        return "user"

    def list_files(self, path: str = "/") -> list[str]:
        if path == "/":
            prefix = "/"
        else:
            prefix = path.rstrip("/") + "/"
        items = set()
        for filepath in self.files:
            if not filepath.startswith(prefix) and filepath != path:
                continue
            rest = filepath[len(prefix):]
            if "/" in rest:
                items.add(rest.split("/")[0] + "/")
            elif rest:
                items.add(rest)
        return sorted(items)

    def list_files_detailed(self, path: str = "/") -> list[dict]:
        """Return list of {name, is_dir, perms, owner, group, size, mtime}."""
        if path == "/":
            prefix = "/"
        else:
            prefix = path.rstrip("/") + "/"

        dirs_seen = set()
        result = []

        for filepath in sorted(self.files.keys()):
            if not filepath.startswith(prefix) and filepath != path:
                continue
            rest = filepath[len(prefix):]
            if not rest:
                continue

            if "/" in rest:
                dirname = rest.split("/")[0]
                if dirname not in dirs_seen:
                    dirs_seen.add(dirname)
                    m = self.file_meta.get(filepath, {})
                    result.append({
                        "name": dirname,
                        "is_dir": True,
                        "perms": "drwxr-xr-x",
                        "owner": m.get("owner", "root"),
                        "group": m.get("group", "root"),
                        "size": 4096,
                        "mtime": m.get("mtime", "Nov 15 14:32"),
                    })
            else:
                content = self.files[filepath]
                m = self.file_meta.get(filepath, {})
                result.append({
                    "name": rest,
                    "is_dir": False,
                    "perms": m.get("perms", "-rw-r--r--"),
                    "owner": m.get("owner", "root"),
                    "group": m.get("group", "root"),
                    "size": len(content.encode()),
                    "mtime": m.get("mtime", "Nov 15 14:32"),
                })

        return result


@dataclass
class Network:
    name: str
    subnet: str
    hosts: list[Host] = field(default_factory=list)
    discovered_hosts: list[str] = field(default_factory=list)

    def get_host(self, ip: str) -> Host | None:
        for host in self.hosts:
            if host.ip == ip:
                return host
        return None

    def get_all_ips(self) -> list[str]:
        return [h.ip for h in self.hosts]

    def discover_host(self, ip: str) -> bool:
        if ip not in self.discovered_hosts:
            self.discovered_hosts.append(ip)
            return True
        return False


def load_network(yaml_path: str | Path) -> Network:
    yaml_path = Path(yaml_path)
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    hosts = []
    for host_data in data.get("hosts", []):
        services = []
        for svc_data in host_data.get("services", []):
            services.append(Service(
                name=svc_data["name"],
                port=svc_data["port"],
                version=svc_data.get("version", ""),
                vulnerable=svc_data.get("vulnerable", False),
                exploit_name=svc_data.get("exploit_name", "") or "",
                credentials=svc_data.get("credentials", {}),
            ))

        custom_files = host_data.get("files", {})
        users = host_data.get("users", [])
        hostname = host_data["hostname"]
        ip = host_data["ip"]
        os_name = host_data.get("os", "Ubuntu 20.04 LTS")

        # Generate realistic filesystem, overlay custom files
        gen_files, gen_meta = generate_linux_fs(
            hostname=hostname,
            ip=ip,
            os_name=os_name,
            users=users,
            services=services,
            custom_files=custom_files,
        )

        # Build environment
        user = users[0]["name"] if users else "root"
        env = {
            "HOME": f"/home/{user}" if user != "root" else "/root",
            "USER": user,
            "LOGNAME": user,
            "SHELL": "/bin/bash",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOSTNAME": hostname,
            "TERM": "xterm-256color",
            "LANG": "en_US.UTF-8",
            "PWD": "/",
        }

        hosts.append(Host(
            ip=ip,
            hostname=hostname,
            os=os_name,
            services=services,
            firewall_level=host_data.get("firewall_level", 0),
            files=gen_files,
            file_meta=gen_meta,
            users=users,
            env=env,
        ))

    return Network(
        name=data["name"],
        subnet=data["subnet"],
        hosts=hosts,
    )
