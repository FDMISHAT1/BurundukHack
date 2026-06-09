"""Save / load game state to JSON."""
import json
from engine.paths import SAVE_DIR

SAVE_FILE = SAVE_DIR / "profile.json"


def save_exists() -> bool:
    return SAVE_FILE.exists()


def save_game(game) -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    # Write .bash_history on localhost for realism
    from ui.prompt import get_history_list
    hist = get_history_list()
    if game.localhost and hist:
        handle = game.player.handle
        bash_hist_path = f"/home/{handle}/.bash_history"
        game.localhost.files[bash_hist_path] = "\n".join(hist[-500:]) + "\n"
        game.localhost.user_files[bash_hist_path] = game.localhost.files[bash_hist_path]

    # --- player ---
    player = game.player
    player_data = {
        "handle": player.handle,
        "password": game._password,
        "reputation": player.reputation,
        "tools_unlocked": player.tools_unlocked,
        "known_credentials": player.known_credentials,
        "completed_missions": player.completed_missions,
        "files_read": list(player.files_read),
        "files_downloaded": list(player.files_downloaded),
    }

    # --- history & aliases ---
    shell_data = {
        "history": hist[-500:],
        "aliases": game.aliases,
    }

    # --- localhost user files (delta only) ---
    localhost_data = {}
    if game.localhost:
        localhost_data = {
            "user_files": game.localhost.user_files,
            "installed_packages": game.localhost.installed_packages,
            "cwd": game.localhost.cwd,
        }

    # --- networks ---
    networks_data = {}
    for net_id, net in game.networks.items():
        net_state = {
            "discovered_hosts": net.discovered_hosts,
            "hosts": {},
        }
        for host in net.hosts:
            net_state["hosts"][host.ip] = {
                "compromised": host.compromised,
                "access_level": host.access_level,
                "user_files": host.user_files,
                "installed_packages": host.installed_packages,
            }
        networks_data[net_id] = net_state

    # --- missions ---
    missions_data = {}
    for mission in game.missions:
        missions_data[mission.id] = {
            "completed_objectives": [o.id for o in mission.objectives if o.completed],
            "hint_index": mission.hint_index,
        }

    data = {
        "version": 1,
        "language": game._language,
        "player": player_data,
        "localhost": localhost_data,
        "networks": networks_data,
        "missions": missions_data,
        "shell": shell_data,
    }

    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_game(game) -> dict:
    """Load save data. Returns the raw dict for game.py to apply."""
    with open(SAVE_FILE, "r") as f:
        return json.load(f)


def apply_save(game, data: dict) -> None:
    """Apply loaded save data to the game state."""
    # --- player ---
    pd = data.get("player", {})
    game.player.handle = pd.get("handle", "hacker")
    game._password = pd.get("password", "")
    game.player.reputation = pd.get("reputation", 0)
    game.player.tools_unlocked = pd.get("tools_unlocked", game.player.tools_unlocked)
    game.player.known_credentials = pd.get("known_credentials", [])
    game.player.completed_missions = pd.get("completed_missions", [])
    game.player.files_read = set(pd.get("files_read", []))
    game.player.files_downloaded = set(pd.get("files_downloaded", []))

    # --- localhost ---
    ld = data.get("localhost", {})
    if game.localhost:
        for path, content in ld.get("user_files", {}).items():
            game.localhost.files[path] = content
            game.localhost.user_files[path] = content
        game.localhost.installed_packages = ld.get("installed_packages", [])
        game.localhost.cwd = ld.get("cwd", f"/home/{game.player.handle}")

    # --- networks ---
    nd = data.get("networks", {})
    for net_id, net_state in nd.items():
        if net_id not in game.networks:
            continue
        net = game.networks[net_id]
        net.discovered_hosts = net_state.get("discovered_hosts", [])
        for ip, host_state in net_state.get("hosts", {}).items():
            host = net.get_host(ip)
            if host:
                host.compromised = host_state.get("compromised", False)
                host.access_level = host_state.get("access_level", "none")
                for path, content in host_state.get("user_files", {}).items():
                    host.files[path] = content
                    host.user_files[path] = content
                host.installed_packages = host_state.get("installed_packages", [])

    # --- missions ---
    md = data.get("missions", {})
    for mission in game.missions:
        ms = md.get(mission.id, {})
        completed_ids = ms.get("completed_objectives", [])
        for obj in mission.objectives:
            if obj.id in completed_ids:
                obj.completed = True
        mission.hint_index = ms.get("hint_index", 0)

    # --- shell (history, aliases) ---
    sd = data.get("shell", {})
    from ui.prompt import _history_list
    saved_hist = sd.get("history", [])
    _history_list.clear()
    _history_list.extend(saved_hist)
    game.aliases.update(sd.get("aliases", {}))
