import yaml
from commands.registry import register
from ui.console import console
from ui.lang import t
from ui.animations import fake_progress
from engine.paths import DATA_DIR
_packages: dict | None = None


def _load_packages() -> dict:
    global _packages
    if _packages is None:
        pkg_path = DATA_DIR / "apt" / "packages.yaml"
        if pkg_path.exists():
            with open(pkg_path) as f:
                _packages = yaml.safe_load(f) or {}
        else:
            _packages = {}
    return _packages


@register("apt", "cmd.apt.help", required_tool="apt")
def handle_apt(game, args):
    if not game.current_host:
        console.print_error(t("fs.not_connected"))
        return

    if not args:
        console.print("""apt 2.0.9 (amd64)
Usage: apt [options] command

Most used commands:
  list - list packages based on package names
  search - search in package descriptions
  install - install packages
  remove - remove packages
  update - update list of available packages
  upgrade - upgrade the system by installing/upgrading packages

See apt(8) for more information about the available commands.""")
        return

    subcmd = args[0]
    sub_args = args[1:]

    if subcmd == "update":
        _apt_update(game)
    elif subcmd == "install":
        _apt_install(game, sub_args)
    elif subcmd == "list":
        _apt_list(game, sub_args)
    elif subcmd == "search":
        _apt_search(game, sub_args)
    elif subcmd == "remove":
        _apt_remove(game, sub_args)
    elif subcmd == "upgrade":
        _apt_upgrade(game)
    else:
        console.print_error(f"apt: unknown command '{subcmd}'")


def _apt_update(game):
    host = game.current_host
    os_low = host.os.lower()

    if "kali" in os_low:
        sources = [
            "http://http.kali.org/kali kali-rolling InRelease",
        ]
    elif "ubuntu" in os_low or "debian" in os_low:
        code = "focal" if "20.04" in host.os else "jammy"
        sources = [
            f"http://archive.ubuntu.com/ubuntu {code} InRelease",
            f"http://archive.ubuntu.com/ubuntu {code}-updates InRelease",
            f"http://security.ubuntu.com/ubuntu {code}-security InRelease",
        ]
    else:
        sources = [
            "http://mirror.centos.org/centos/7/os/x86_64/repodata/repomd.xml",
            "http://mirror.centos.org/centos/7/updates/x86_64/repodata/repomd.xml",
        ]

    for src in sources:
        console.print(f"[dim]Hit:{src}[/dim]")

    fake_progress(t("apt.updating"), seconds=2.0)
    pkgs = _load_packages()
    total = len(pkgs.get("packages", []))
    console.print(f"[green]Reading package lists... Done[/green]")
    console.print(f"Building dependency tree... Done")
    console.print(f"Reading state information... Done")
    console.print(f"{total} packages can be looked up.")


def _apt_install(game, args):
    if not args:
        console.print_error("apt install: missing package name")
        return

    host = game.current_host
    if host.access_level != "root":
        console.print_error("E: Could not open lock file - open (13: Permission denied)")
        console.print_error("E: Unable to acquire the dpkg frontend lock. Are you root?")
        return

    pkgs = _load_packages()
    all_packages = {p["name"]: p for p in pkgs.get("packages", [])}

    for pkg_name in args:
        if pkg_name.startswith("-"):
            continue

        if pkg_name in host.installed_packages:
            console.print(f"{pkg_name} is already the newest version.")
            continue

        if pkg_name not in all_packages:
            console.print_error(f"E: Unable to locate package {pkg_name}")
            continue

        pkg = all_packages[pkg_name]
        size = pkg.get("size", "1,024 kB")
        version = pkg.get("version", "1.0-1")

        console.print(f"Reading package lists... Done")
        console.print(f"The following NEW packages will be installed:")
        console.print(f"  [green]{pkg_name}[/green]")
        console.print(f"0 upgraded, 1 newly installed, 0 to remove.")
        console.print(f"Need to get {size} of archives.")

        fake_progress(f"Installing {pkg_name} ({version})", seconds=2.5)

        host.installed_packages.append(pkg_name)

        # Add binary to filesystem
        if pkg.get("binary"):
            host.files[f"/usr/bin/{pkg['binary']}"] = \
                "[ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked]"
            host.file_meta[f"/usr/bin/{pkg['binary']}"] = {
                "perms": "-rwxr-xr-x", "owner": "root", "group": "root", "mtime": "Nov 15 14:35"
            }

        # Unlock tool if applicable
        if pkg.get("unlocks_tool"):
            tool = pkg["unlocks_tool"]
            if tool not in game.player.tools_unlocked:
                game.player.tools_unlocked.append(tool)
                console.print_success(f"Tool unlocked: {tool}")

        console.print(f"Setting up {pkg_name} ({version}) ...")
        console.print(f"[green]{pkg_name} ({version}) installed successfully.[/green]")


def _apt_list(game, args):
    host = game.current_host
    installed_only = "--installed" in args

    if installed_only:
        if not host.installed_packages:
            console.print("Listing... Done")
            return
        for pkg_name in sorted(host.installed_packages):
            console.print(f"{pkg_name}/now [installed]")
    else:
        pkgs = _load_packages()
        for p in pkgs.get("packages", []):
            name = p["name"]
            version = p.get("version", "1.0-1")
            status = "[installed]" if name in host.installed_packages else ""
            console.print(f"{name}/{version} amd64 {status}")


def _apt_search(game, args):
    if not args:
        console.print_error("apt search: missing search term")
        return

    query = args[0].lower()
    pkgs = _load_packages()
    found = False

    for p in pkgs.get("packages", []):
        name = p["name"]
        desc = p.get("description", "")
        if query in name.lower() or query in desc.lower():
            console.print(f"[green]{name}[/green] - {desc}")
            found = True

    if not found:
        console.print(f"No packages found matching '{args[0]}'")


def _apt_remove(game, args):
    if not args:
        console.print_error("apt remove: missing package name")
        return

    host = game.current_host
    if host.access_level != "root":
        console.print_error("E: Could not open lock file - open (13: Permission denied)")
        return

    for pkg_name in args:
        if pkg_name in host.installed_packages:
            host.installed_packages.remove(pkg_name)
            console.print(f"Removing {pkg_name} ...")
            console.print(f"[green]{pkg_name} removed.[/green]")
        else:
            console.print_error(f"Package '{pkg_name}' is not installed")


def _apt_upgrade(game):
    host = game.current_host
    if host.access_level != "root":
        console.print_error("E: Could not open lock file - open (13: Permission denied)")
        return

    fake_progress("Upgrading packages", seconds=3.0)
    console.print("0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.")
