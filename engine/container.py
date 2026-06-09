"""
Docker container management for BurundukHack.
Manages container lifecycle, command execution, and network setup.
Falls back gracefully when Docker is not available.
"""
import subprocess
import shlex

# Docker availability flag
_docker_available = None
_docker_mode = None  # "full", "lite", None


def check_docker() -> bool:
    """Check if Docker is available and running."""
    global _docker_available
    if _docker_available is not None:
        return _docker_available
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=5
        )
        _docker_available = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _docker_available = False
    return _docker_available


def get_docker_mode() -> str | None:
    """Return current Docker mode: 'full', 'lite', or None."""
    return _docker_mode


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

from engine.paths import DATA_DIR, DOCKER_DIR
CONFIG_PATH = DATA_DIR / "docker_config.yaml"

DEFAULT_CONFIG = {
    "enabled": False,
    "base_image": "debian",       # "debian" or "alpine"
    "memory_limit": "128m",       # per container
    "cpu_limit": 0.5,             # per container
    "network_subnet": "192.168.1.0/24",
    "auto_cleanup": True,         # remove containers on exit
}


def load_config() -> dict:
    """Load Docker configuration."""
    if CONFIG_PATH.exists():
        import yaml
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
        merged = {**DEFAULT_CONFIG, **cfg}
        return merged
    return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    """Save Docker configuration."""
    import yaml
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


# ---------------------------------------------------------------------------
# Image building
# ---------------------------------------------------------------------------

# DOCKER_DIR imported from engine.paths

# Package lists per role
PACKAGES = {
    "kali": {
        "debian": (
            "bash coreutils grep sed gawk findutils procps net-tools "
            "iputils-ping iproute2 curl wget netcat-openbsd nmap dnsutils "
            "openssh-client vim-tiny nano less file tree "
            "python3 gcc make git "
            "whois traceroute tcpdump socat "
            "tar gzip bzip2 xz-utils zip unzip "
            "diffutils patch bc dc "
            "sudo passwd"
        ),
        "alpine": (
            "bash coreutils grep sed gawk findutils procps net-tools "
            "iputils iproute2 curl wget nmap-ncat nmap bind-tools "
            "openssh-client vim nano less file tree "
            "python3 gcc make git "
            "whois traceroute tcpdump socat "
            "tar gzip bzip2 xz zip unzip "
            "diffutils patch bc "
            "sudo shadow"
        ),
    },
    "ubuntu_target": {
        "debian": "bash openssh-server sudo coreutils procps net-tools python3 vim-tiny less",
        "alpine": "bash openssh shadow sudo coreutils procps net-tools python3 vim less",
    },
    "db_server": {
        "debian": "bash openssh-server sudo coreutils procps net-tools mariadb-server python3",
        "alpine": "bash openssh shadow sudo coreutils procps net-tools mariadb python3",
    },
    "router": {
        "debian": "bash iproute2 iptables net-tools procps",
        "alpine": "bash iproute2 net-tools procps",
    },
}


def _generate_dockerfile(role: str, base: str, users: list[dict] | None = None,
                         services: list[dict] | None = None) -> str:
    """Generate a Dockerfile for a given role and base image."""
    if base == "alpine":
        base_image = "alpine:3.19"
        install_cmd = "apk add --no-cache"
        ssh_setup = (
            "RUN ssh-keygen -A && "
            "mkdir -p /run/sshd && "
            "sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && "
            "sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config"
        )
    else:
        base_image = "debian:bookworm-slim"
        install_cmd = "apt-get update && apt-get install -y --no-install-recommends"
        ssh_setup = (
            "RUN mkdir -p /run/sshd && "
            "sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && "
            "sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config"
        )

    pkgs = PACKAGES.get(role, PACKAGES["ubuntu_target"]).get(base, "bash coreutils")

    lines = [f"FROM {base_image}", ""]

    # Install packages
    if base == "alpine":
        lines.append(f"RUN {install_cmd} {pkgs}")
    else:
        lines.append(f"RUN {install_cmd} \\")
        lines.append(f"    {pkgs} \\")
        lines.append(f"    && rm -rf /var/lib/apt/lists/*")
    lines.append("")

    # SSH setup for target/server roles
    has_ssh = services and any(s.get("name") == "ssh" for s in services)
    if has_ssh or role in ("ubuntu_target", "db_server"):
        lines.append(ssh_setup)
        lines.append("")

    # Kali-specific setup
    if role == "kali":
        lines.append("")
        lines.append('RUN echo "export PS1=\\"\\\\u@kali:\\\\w\\\\$ \\"" >> /etc/bash.bashrc')
        if base == "alpine":
            lines.append("RUN adduser -D -s /bin/bash pentester 2>/dev/null; echo 'pentester:pentester' | chpasswd")
            lines.append("RUN echo 'pentester ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers")
        else:
            lines.append("RUN useradd -m -s /bin/bash -G sudo pentester 2>/dev/null; echo 'pentester:pentester' | chpasswd")
            lines.append("RUN echo 'pentester ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers")
        lines.append("USER pentester")
        lines.append("WORKDIR /home/pentester")
        lines.append("RUN mkdir -p loot .ssh")
    else:
        # Create users for non-kali roles
        if users:
            for user in users:
                name = user.get("name", "user")
                shell = user.get("shell", "/bin/bash")
                if base == "alpine":
                    lines.append(f"RUN adduser -D -s {shell} {name} && echo '{name}:{user.get('password', name)}' | chpasswd")
                else:
                    lines.append(f"RUN useradd -m -s {shell} {name} && echo '{name}:{user.get('password', name)}' | chpasswd")

    lines.append("")
    lines.append('CMD ["sleep", "infinity"]')
    return "\n".join(lines)


def build_image(role: str, base: str, tag: str, users: list[dict] | None = None,
                services: list[dict] | None = None,
                on_progress=None) -> bool:
    """Build a Docker image for a given role."""
    dockerfile_content = _generate_dockerfile(role, base, users, services)

    # Write temp Dockerfile
    build_dir = DOCKER_DIR / role
    build_dir.mkdir(parents=True, exist_ok=True)
    dockerfile_path = build_dir / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content)

    # Write MOTD for kali
    if role == "kali":
        (build_dir / "motd").write_text(
            "\n  BurundukHack Pentesting Workstation\n"
            "  Type 'help' for available commands.\n\n"
        )

    if on_progress:
        on_progress(f"Building {tag}...")

    result = subprocess.run(
        ["docker", "build", "-t", tag, "-f", str(dockerfile_path), str(build_dir)],
        capture_output=True, text=True, timeout=300
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Network management
# ---------------------------------------------------------------------------

NETWORK_NAME_PREFIX = "bhack_"


def create_network(name: str, subnet: str) -> bool:
    """Create a Docker network with a specific subnet."""
    net_name = f"{NETWORK_NAME_PREFIX}{name}"
    # Check if already exists
    result = subprocess.run(
        ["docker", "network", "inspect", net_name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return True  # already exists

    result = subprocess.run(
        ["docker", "network", "create",
         "--subnet", subnet,
         "--driver", "bridge",
         net_name],
        capture_output=True, text=True
    )
    return result.returncode == 0


def remove_network(name: str):
    """Remove a Docker network."""
    subprocess.run(
        ["docker", "network", "rm", f"{NETWORK_NAME_PREFIX}{name}"],
        capture_output=True, text=True
    )


# ---------------------------------------------------------------------------
# Container lifecycle
# ---------------------------------------------------------------------------

CONTAINER_PREFIX = "bhack_"


class DockerHost:
    """Represents a Docker container acting as a network host."""

    def __init__(self, name: str, ip: str, image: str, network: str,
                 hostname: str = "", role: str = "ubuntu_target",
                 services: list[dict] | None = None,
                 memory: str = "128m", cpus: float = 0.5):
        self.name = f"{CONTAINER_PREFIX}{name}"
        self.ip = ip
        self.image = image
        self.network = f"{NETWORK_NAME_PREFIX}{network}"
        self.hostname = hostname or name
        self.role = role
        self.services = services or []
        self.memory = memory
        self.cpus = cpus
        self.container_id: str | None = None
        self.running = False

    def start(self) -> bool:
        """Start the container."""
        # Check if already running
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", self.name],
            capture_output=True, text=True
        )
        if result.returncode == 0 and "true" in result.stdout.lower():
            self.running = True
            self.container_id = self._get_container_id()
            return True

        # Remove if exists but stopped
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)

        # Build run command
        cmd = [
            "docker", "run", "-d",
            "--name", self.name,
            "--hostname", self.hostname,
            "--network", self.network,
            "--ip", self.ip,
            "--memory", self.memory,
            f"--cpus={self.cpus}",
            "--restart", "no",
        ]

        # Expose ports for services
        for svc in self.services:
            port = svc.get("port")
            if port:
                cmd.extend(["--expose", str(port)])

        cmd.append(self.image)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            self.container_id = result.stdout.strip()[:12]
            self.running = True

            # Start services inside container
            self._start_services()
            return True
        return False

    def stop(self):
        """Stop and remove the container."""
        subprocess.run(
            ["docker", "rm", "-f", self.name],
            capture_output=True, text=True
        )
        self.running = False
        self.container_id = None

    def exec(self, command: str, user: str = "", timeout: int = 10,
             stdin_data: str | None = None) -> tuple[int, str, str]:
        """Execute a command in the container. Returns (exit_code, stdout, stderr)."""
        cmd = ["docker", "exec"]
        if user:
            cmd.extend(["-u", user])
        if stdin_data:
            cmd.append("-i")
        cmd.extend([self.name, "bash", "-c", command])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=timeout,
                input=stdin_data
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "Command timed out"

    def exec_interactive(self, command: str, user: str = "") -> tuple[int, str, str]:
        """Execute with longer timeout for interactive-like commands."""
        return self.exec(command, user=user, timeout=30)

    def put_file(self, container_path: str, content: str):
        """Write a file into the container."""
        # Use docker exec with heredoc
        self.exec(f"cat > {shlex.quote(container_path)}", stdin_data=content)

    def get_file(self, container_path: str) -> str | None:
        """Read a file from the container."""
        rc, stdout, _ = self.exec(f"cat {shlex.quote(container_path)}")
        return stdout if rc == 0 else None

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in the container."""
        rc, _, _ = self.exec(f"test -e {shlex.quote(path)}")
        return rc == 0

    def is_running(self) -> bool:
        """Check if container is still running."""
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", self.name],
            capture_output=True, text=True
        )
        self.running = result.returncode == 0 and "true" in result.stdout.lower()
        return self.running

    def _get_container_id(self) -> str | None:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.Id}}", self.name],
            capture_output=True, text=True
        )
        return result.stdout.strip()[:12] if result.returncode == 0 else None

    def _start_services(self):
        """Start services (SSH, HTTP, etc.) inside the container."""
        for svc in self.services:
            name = svc.get("name", "")
            if name == "ssh":
                # Start SSH daemon
                self.exec("mkdir -p /run/sshd", user="root")
                self.exec("/usr/sbin/sshd", user="root")
            elif name == "http":
                # Simple python HTTP server
                port = svc.get("port", 80)
                self.exec(
                    f"python3 -m http.server {port} --directory /var/www/html &",
                    user="root"
                )
            elif name == "mysql":
                self.exec("mysqld_safe &", user="root")


# ---------------------------------------------------------------------------
# Game-level orchestrator
# ---------------------------------------------------------------------------

class ContainerManager:
    """Manages all Docker containers for a game session."""

    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self.hosts: dict[str, DockerHost] = {}  # ip -> DockerHost
        self.networks: dict[str, str] = {}      # net_name -> subnet
        self.localhost: DockerHost | None = None
        self.enabled = self.config.get("enabled", False) and check_docker()

    @property
    def is_docker_mode(self) -> bool:
        return self.enabled

    def setup_network(self, network_name: str, subnet: str,
                      hosts_config: list[dict], on_progress=None) -> bool:
        """Set up a full network with all hosts from mission config."""
        if not self.enabled:
            return False

        base = self.config.get("base_image", "debian")
        mem = self.config.get("memory_limit", "128m")
        cpus = self.config.get("cpu_limit", 0.5)

        # Create Docker network
        if on_progress:
            on_progress(f"Creating network {network_name}...")
        if not create_network(network_name, subnet):
            return False
        self.networks[network_name] = subnet

        # Build images and start containers
        for host_cfg in hosts_config:
            ip = host_cfg["ip"]
            hostname = host_cfg.get("hostname", f"host-{ip.split('.')[-1]}")
            role = host_cfg.get("role", "ubuntu_target")
            users = host_cfg.get("users", [])
            services = host_cfg.get("services", [])
            custom_files = host_cfg.get("files", {})

            # Determine image tag
            tag = f"bhack_{role}_{base}"

            # Build image if not exists
            result = subprocess.run(
                ["docker", "image", "inspect", tag],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                if on_progress:
                    on_progress(f"Building image {tag}...")
                if not build_image(role, base, tag, users, services, on_progress):
                    if on_progress:
                        on_progress(f"Failed to build {tag}, skipping {hostname}")
                    continue

            # Create and start container
            if on_progress:
                on_progress(f"Starting {hostname} ({ip})...")

            docker_host = DockerHost(
                name=f"{network_name}_{hostname}",
                ip=ip, image=tag, network=network_name,
                hostname=hostname, role=role,
                services=services, memory=mem, cpus=cpus
            )

            if docker_host.start():
                self.hosts[ip] = docker_host

                # Deploy custom files
                for path, content in custom_files.items():
                    docker_host.put_file(path, content)

                # Create users with credentials
                for user in users:
                    uname = user.get("name", "user")
                    pwd = user.get("password", uname)
                    docker_host.exec(
                        f"id {uname} 2>/dev/null || "
                        f"(useradd -m -s /bin/bash {uname} 2>/dev/null || "
                        f"adduser -D -s /bin/bash {uname} 2>/dev/null) && "
                        f"echo '{uname}:{pwd}' | chpasswd",
                        user="root"
                    )

                if on_progress:
                    on_progress(f"  {hostname} ({ip}) started")
            else:
                if on_progress:
                    on_progress(f"  Failed to start {hostname}")

        return True

    def setup_localhost(self, network_name: str, ip: str = "10.10.10.5",
                       handle: str = "pentester", on_progress=None) -> DockerHost | None:
        """Set up the player's localhost container."""
        if not self.enabled:
            return None

        base = self.config.get("base_image", "debian")
        tag = f"bhack_kali_{base}"
        mem = self.config.get("memory_limit", "128m")
        cpus = self.config.get("cpu_limit", 0.5)

        # Build kali image
        result = subprocess.run(
            ["docker", "image", "inspect", tag],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            if on_progress:
                on_progress("Building Kali workstation image...")
            build_image("kali", base, tag, on_progress=on_progress)

        # Use the mission network directly
        net = network_name

        if on_progress:
            on_progress("Starting Kali workstation...")

        localhost = DockerHost(
            name="localhost_kali",
            ip=ip, image=tag, network=net,
            hostname="kali", role="kali",
            memory=mem, cpus=cpus
        )

        if localhost.start():
            # Set up user
            localhost.exec(
                f"(id {handle} 2>/dev/null || "
                f"(useradd -m -s /bin/bash {handle} 2>/dev/null || "
                f"adduser -D -s /bin/bash {handle} 2>/dev/null)) && "
                f"echo '{handle}:{handle}' | chpasswd && "
                f"mkdir -p /home/{handle}/loot /home/{handle}/.ssh",
                user="root"
            )
            self.localhost = localhost
            self.hosts[ip] = localhost
            if on_progress:
                on_progress("Kali workstation ready")
            return localhost

        return None

    def exec_on_host(self, ip: str, command: str, user: str = "",
                     stdin_data: str | None = None) -> tuple[int, str, str]:
        """Execute a command on a specific host."""
        host = self.hosts.get(ip)
        if not host:
            return 127, "", f"Host {ip} not found"
        return host.exec(command, user=user, stdin_data=stdin_data)

    def cleanup(self):
        """Stop all containers and remove networks."""
        for host in self.hosts.values():
            host.stop()
        self.hosts.clear()

        if self.config.get("auto_cleanup", True):
            for net_name in list(self.networks.keys()):
                remove_network(net_name)
            # Also remove mgmt network
            remove_network("mgmt")
        self.networks.clear()
        self.localhost = None

    def get_host(self, ip: str) -> DockerHost | None:
        return self.hosts.get(ip)

    def list_hosts(self) -> list[str]:
        return list(self.hosts.keys())
