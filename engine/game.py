import yaml

from engine.network import Network, Host, load_network
from engine.player import Player
from engine.mission import Mission, load_mission
from engine.filesystem import generate_linux_fs
from engine.save import save_exists, save_game, load_game, apply_save
from ui.console import console
from ui.lang import load_lang, t
from ui import banners
from ui.animations import fake_progress
from ui.prompt import init_prompt, prompt_input
from commands.registry import dispatch, COMMANDS
from engine.shell import init_shell, process_line

# Import command modules to trigger registration
import commands.general_cmds
import commands.network_cmds
import commands.exploit_cmds
import commands.filesystem_cmds
import commands.social_cmds
import commands.linux_cmds
import commands.apt_cmds
import commands.file_edit_cmds
import commands.ctf_cmds
import commands.text_cmds
import commands.shell_builtins
import commands.net_tools
import commands.sysadmin_cmds
import commands.extra_cmds


from engine.paths import DATA_DIR

INSTALLER_LOGO = r"""[bold green]
 ____                            _       _     ___  ____
| __ ) _   _ _ __ _   _ _ __   __| |_   _| | __/ _ \/ ___|
|  _ \| | | | '__| | | | '_ \ / _` | | | | |/ / | | \___ \
| |_) | |_| | |  | |_| | | | | (_| | |_| |   <| |_| |___) |
|____/ \__,_|_|   \__,_|_| |_|\__,_|\__,_|_|\_\\___/|____/
[/bold green]
[dim cyan]        Advanced Penetration Testing OS 2024.3[/dim cyan]
[dim white]                 Installer v1.0[/dim white]
"""

LOGIN_LOGO = r"""[bold green]
 ____                            _       _     ___  ____
| __ ) _   _ _ __ _   _ _ __   __| |_   _| | __/ _ \/ ___|
|  _ \| | | | '__| | | | '_ \ / _` | | | | |/ / | | \___ \
| |_) | |_| | |  | |_| | | | | (_| | |_| |   <| |_| |___) |
|____/ \__,_|_|   \__,_|_| |_|\__,_|\__,_|_|\_\\___/|____/
[/bold green]
[dim cyan]          Advanced Penetration Testing OS 2024.3[/dim cyan]
"""


def _create_localhost(handle: str) -> Host:
    users = [{"name": handle, "role": "Pentester", "email": f"{handle}@localhost"}]
    custom_files = {
        f"/home/{handle}/README.txt": (
            "=== BurundukOS Workstation ===\n\n"
            "Your pentesting workstation is ready.\n"
            "Use 'missions' to see your current objectives.\n"
            "Use 'nmap' to start scanning target networks.\n"
            "Downloaded loot will appear in ~/loot/\n"
        ),
        f"/home/{handle}/loot/.keep": "",
        f"/home/{handle}/.bash_history": (
            "sudo apt update\n"
            "nmap --help\n"
            "cat /etc/os-release\n"
        ),
    }
    attacker_ip = "10.10.10.5"
    gen_files, gen_meta = generate_linux_fs(
        hostname="kali",
        ip=attacker_ip,
        os_name="Kali GNU/Linux 2024.3",
        users=users,
        services=[],
        custom_files=custom_files,
    )
    env = {
        "HOME": f"/home/{handle}",
        "USER": handle,
        "LOGNAME": handle,
        "SHELL": "/bin/bash",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOSTNAME": "kali",
        "TERM": "xterm-256color",
        "LANG": "en_US.UTF-8",
        "PWD": f"/home/{handle}",
    }
    return Host(
        ip=attacker_ip,
        hostname="kali",
        os="Kali GNU/Linux 2024.3",
        services=[],
        compromised=True,
        access_level="user",
        files=gen_files,
        file_meta=gen_meta,
        users=users,
        cwd=f"/home/{handle}",
        env=env,
    )


class Game:
    def __init__(self):
        self.player = Player()
        self.localhost: Host | None = None
        self.current_network: Network | None = None
        self.current_host: Host | None = None
        self.current_mission: Mission | None = None
        self.networks: dict[str, Network] = {}
        self.missions: list[Mission] = []
        self.wordlist: list[str] = []
        self.running = False
        self._password = ""
        self._language = "en"
        # Shell state
        self.last_exit_code = 0
        self.stdin: str | None = None      # piped/redirected input for current command
        self.shell_vars: dict[str, str] = {}  # non-exported shell variables
        self.aliases: dict[str, str] = {}     # shell aliases
        # Docker mode
        self.container_manager = None         # ContainerManager instance
        self._docker_mode = False

    # ------------------------------------------------------------------
    #  Installer (first run)
    # ------------------------------------------------------------------

    def _run_installer(self):
        console.print(INSTALLER_LOGO)
        console.print()

        # [1/4] Language
        console.print("[bold bright_white]\\[1/4] Select language / Выберите язык[/bold bright_white]")
        console.print()
        console.print("  [green]1.[/green] English")
        console.print("  [green]2.[/green] Русский")
        console.print()
        try:
            choice = console.input("[bold green]> [/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"
        self._language = "ru" if choice == "2" else "en"
        load_lang(self._language)
        console.print()

        # [2/4] Username
        console.print(f"[bold bright_white]\\[2/4] {t('installer.create_user')}[/bold bright_white]")
        console.print()
        try:
            handle = console.input(f"  {t('installer.username')} ").strip()
        except (EOFError, KeyboardInterrupt):
            handle = ""
        if not handle:
            handle = "hacker"
        self.player.handle = handle
        console.print()

        # [3/4] Password
        console.print(f"[bold bright_white]\\[3/4] {t('installer.set_password')}[/bold bright_white]")
        console.print()
        try:
            pw1 = console.input(f"  {t('installer.password')} ").strip()
        except (EOFError, KeyboardInterrupt):
            pw1 = "toor"
        if not pw1:
            pw1 = "toor"
        try:
            pw2 = console.input(f"  {t('installer.confirm')} ").strip()
        except (EOFError, KeyboardInterrupt):
            pw2 = pw1
        if pw1 != pw2:
            console.print_warning(t("installer.mismatch"))
            pw1 = pw1  # just use first one
        self._password = pw1
        console.print()

        # [4/5] Docker mode selection
        console.print(f"[bold bright_white]\\[4/5] Docker Mode[/bold bright_white]")
        console.print()
        from engine.container import check_docker, load_config, save_config
        docker_ok = check_docker()
        if docker_ok:
            console.print("  [green]Docker detected![/green] Real containers = real Linux commands.")
            console.print()
            console.print("  [green]1.[/green] Full (Debian) — ~300 MB RAM, all tools")
            console.print("  [green]2.[/green] Lite (Alpine) — ~50 MB RAM, lightweight")
            console.print("  [green]3.[/green] Off — virtual mode (no Docker)")
            console.print()
            try:
                dchoice = console.input("[bold green]> [/bold green]").strip()
            except (EOFError, KeyboardInterrupt):
                dchoice = "3"
            docker_cfg = load_config()
            if dchoice == "1":
                docker_cfg["enabled"] = True
                docker_cfg["base_image"] = "debian"
                docker_cfg["memory_limit"] = "256m"
                self._docker_mode = True
            elif dchoice == "2":
                docker_cfg["enabled"] = True
                docker_cfg["base_image"] = "alpine"
                docker_cfg["memory_limit"] = "64m"
                self._docker_mode = True
            else:
                docker_cfg["enabled"] = False
                self._docker_mode = False
            save_config(docker_cfg)
        else:
            console.print("  [dim]Docker not detected. Using virtual mode.[/dim]")
            console.print("  [dim]Install Docker for real container experience.[/dim]")
            self._docker_mode = False
        console.print()

        # [5/5] Installing
        console.print(f"[bold bright_white]\\[5/5] {t('installer.installing')}[/bold bright_white]")
        console.print()
        steps = [
            t("installer.step_base"),
            t("installer.step_kernel"),
            t("installer.step_network"),
            t("installer.step_tools"),
            t("installer.step_user"),
            t("installer.step_grub"),
        ]
        for step in steps:
            fake_progress(step, seconds=1.0, steps=50)

        console.print()
        console.print(f"[bold green]{t('installer.complete')}[/bold green]")
        console.print()
        fake_progress(t("installer.rebooting"), seconds=1.5, steps=30)

        # Clear screen for fresh start
        console.console.clear()

    # ------------------------------------------------------------------
    #  Login screen (subsequent runs)
    # ------------------------------------------------------------------

    def _run_login(self, saved_data: dict) -> bool:
        self._language = saved_data.get("language", "en")
        load_lang(self._language)

        saved_handle = saved_data.get("player", {}).get("handle", "hacker")
        saved_password = saved_data.get("player", {}).get("password", "")

        console.print(LOGIN_LOGO)
        console.print(f"[dim]  BurundukOS 2024.3 localhost tty1[/dim]")
        console.print()

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                username = console.input(f"  {t('login.username')} ").strip()
                password = console.input(f"  {t('login.password')} ").strip()
            except (EOFError, KeyboardInterrupt):
                return False

            if username == saved_handle and password == saved_password:
                console.print()
                console.print(f"[dim]Last login: Thu Nov 14 09:15:23 2024 on tty1[/dim]")
                console.print()
                return True
            else:
                console.print_error(t("login.failed"))
                console.print()

        console.print_error(t("login.locked"))
        return False

    # ------------------------------------------------------------------
    #  Core
    # ------------------------------------------------------------------

    def return_to_localhost(self):
        self.current_host = self.localhost
        self.player.connected_to = None

    def is_on_localhost(self) -> bool:
        return self.current_host is self.localhost

    def load_data(self):
        wordlist_path = DATA_DIR / "wordlists" / "common_passwords.yaml"
        if wordlist_path.exists():
            with open(wordlist_path) as f:
                data = yaml.safe_load(f)
                self.wordlist = data.get("passwords", [])

        missions_dir = DATA_DIR / "missions"
        if missions_dir.exists():
            for yaml_file in sorted(missions_dir.glob("*.yaml")):
                mission = load_mission(yaml_file)
                self.missions.append(mission)

        networks_dir = DATA_DIR / "networks"
        if networks_dir.exists():
            for yaml_file in sorted(networks_dir.glob("*.yaml")):
                network = load_network(yaml_file)
                net_id = yaml_file.stem
                self.networks[net_id] = network

    def _update_localhost_hosts_file(self):
        """Add target network hostnames to localhost /etc/hosts."""
        if not self.localhost:
            return
        hosts_path = "/etc/hosts"
        if hosts_path not in self.localhost.files:
            return
        content = self.localhost.files[hosts_path]
        extra_lines = []
        for net in self.networks.values():
            for host in net.hosts:
                # Don't duplicate if already there
                if host.ip not in content:
                    extra_lines.append(f"{host.ip}\t{host.hostname}")
        if extra_lines:
            content = content.rstrip("\n") + "\n\n# Target networks\n" + "\n".join(extra_lines) + "\n"
            self.localhost.files[hosts_path] = content

    def start_mission(self, mission: Mission):
        self.current_mission = mission
        net_id = mission.network_id
        if net_id in self.networks:
            self.current_network = self.networks[net_id]
        else:
            console.print_error(t("game.network_not_found", net_id=net_id))
            return
        banners.show_mission_briefing(
            mission.title, mission.briefing, mission.objectives,
        )

    def _init_docker(self):
        """Initialize Docker containers if Docker mode is enabled."""
        from engine.container import ContainerManager, load_config, check_docker
        cfg = load_config()
        if not cfg.get("enabled") or not check_docker():
            self._docker_mode = False
            return

        self._docker_mode = True
        self.container_manager = ContainerManager(cfg)

        def progress(msg):
            console.print_info(msg)

        # Set up the mission network containers
        if self.current_network:
            hosts_config = []
            for host in self.current_network.hosts:
                host_cfg = {
                    "ip": host.ip,
                    "hostname": host.hostname,
                    "role": "ubuntu_target",
                    "users": [{"name": u.get("name", "user"),
                               "password": u.get("password", u.get("name", "user"))}
                              for u in host.users] if host.users else [],
                    "services": [{"name": s.name, "port": s.port}
                                 for s in host.services],
                    "files": dict(host.user_files) if hasattr(host, "user_files") else {},
                }
                # Detect role from services
                if any(s.name == "mysql" for s in host.services):
                    host_cfg["role"] = "db_server"
                elif host.hostname and "router" in host.hostname.lower():
                    host_cfg["role"] = "router"
                hosts_config.append(host_cfg)

            self.container_manager.setup_network(
                network_name=self.current_mission.network_id if self.current_mission else "default",
                subnet=self.current_network.subnet,
                hosts_config=hosts_config,
                on_progress=progress,
            )

        # Set up localhost — use .254 in the mission subnet
        net_name = self.current_mission.network_id if self.current_mission else "default"
        subnet = self.current_network.subnet if self.current_network else "192.168.1.0/24"
        # Derive .254 from subnet
        base = subnet.rsplit(".", 1)[0]
        kali_ip = f"{base}.254"
        self.container_manager.setup_localhost(
            network_name=net_name,
            ip=kali_ip,
            handle=self.player.handle,
            on_progress=progress,
        )

        console.print_info("Docker environment ready")
        console.print()

    def build_prompt_ansi(self) -> str:
        """Build prompt with ANSI codes for prompt_toolkit."""
        handle = self.player.handle
        if self.is_on_localhost():
            return f"\033[32m{handle}@kali\033[0m$ "
        if self.current_host:
            ip = self.current_host.ip
            if self.current_host.access_level == "root":
                return f"\033[1;31m{handle}@{ip}\033[0m# "
            else:
                return f"\033[31m{handle}@{ip}\033[0m$ "
        return f"\033[32m{handle}@kali\033[0m$ "

    def check_objective(self, objective_type: str, **kwargs):
        if not self.current_mission:
            return
        obj = self.current_mission.check_objective(objective_type, **kwargs)
        if obj:
            console.print()
            console.print(f"[bold bright_green]{t('game.objective_complete', desc=obj.description)}[/bold bright_green]")
            console.print()
            if self.current_mission.is_complete():
                self._complete_mission()

    def _complete_mission(self):
        mission = self.current_mission
        banners.show_mission_complete(mission.title, mission.rewards)
        self.player.reputation += mission.rewards.get("reputation", 0)
        for tool in mission.rewards.get("unlock_tools", []):
            if tool not in self.player.tools_unlocked:
                self.player.tools_unlocked.append(tool)
        self.player.completed_missions.append(mission.id)
        self.return_to_localhost()
        console.print(f"[bold bright_white]{t('game.quit_or_continue')}[/bold bright_white]")
        console.print()

    # ------------------------------------------------------------------
    #  Main
    # ------------------------------------------------------------------

    def run(self):
        self.running = True

        if save_exists():
            # --- Returning user: login ---
            saved_data = load_game(self)
            if not self._run_login(saved_data):
                return

            self.load_data()
            self.localhost = _create_localhost(
                saved_data.get("player", {}).get("handle", "hacker")
            )
            self.current_host = self.localhost
            self._update_localhost_hosts_file()
            apply_save(self, saved_data)

            # Find current mission (first incomplete)
            for m in self.missions:
                if not m.is_complete():
                    self.current_mission = m
                    net_id = m.network_id
                    if net_id in self.networks:
                        self.current_network = self.networks[net_id]
                    break

            console.print_info(t("game.welcome", handle=f"[bold]{self.player.handle}[/bold]"))
            console.print()

        else:
            # --- First run: installer ---
            self._run_installer()

            banners.show_splash()
            console.print()
            console.print_info(t("game.welcome", handle=f"[bold]{self.player.handle}[/bold]"))
            console.print()

            self.localhost = _create_localhost(self.player.handle)
            self.current_host = self.localhost
            self.load_data()
            self._update_localhost_hosts_file()

            if not self.missions:
                console.print_error(t("game.no_missions"))
                return

            self.start_mission(self.missions[0])

        # Init Docker mode if enabled
        self._init_docker()

        # Init prompt_toolkit and shell processor
        init_prompt(list(COMMANDS.keys()), game=self)
        # Use docker dispatch if Docker mode, otherwise Python dispatch
        if self._docker_mode and self.container_manager and self.container_manager.is_docker_mode:
            from engine.docker_dispatch import docker_dispatch
            init_shell(self, docker_dispatch)
        else:
            init_shell(self, dispatch)
        self._stdin = None

        # Default bash aliases (like real .bashrc)
        self.aliases.setdefault("ll", "ls -lah")
        self.aliases.setdefault("la", "ls -la")
        self.aliases.setdefault("l", "ls -CF")
        self.aliases.setdefault("cls", "clear")
        self.aliases.setdefault("..","cd ..")
        self.aliases.setdefault("...","cd ../..")

        # --- Main game loop ---
        while self.running:
            try:
                prompt_str = self.build_prompt_ansi()
                raw = prompt_input(prompt_str)
                raw = raw.strip()
                if raw:
                    process_line(raw)
            except EOFError:
                console.print()
                console.print(f"[bold green]{t('game.use_quit')}[/bold green]")
            except KeyboardInterrupt:
                console.print()
            except Exception as e:
                console.print_error(t("game.error", error=str(e)))

        # Cleanup Docker containers
        if self.container_manager:
            try:
                console.print_info("Stopping containers...")
                self.container_manager.cleanup()
            except Exception:
                pass

        # Auto-save on quit
        try:
            save_game(self)
            console.print_info(t("game.saved"))
        except Exception:
            pass
