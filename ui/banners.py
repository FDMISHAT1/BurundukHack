from ui.console import console
from ui.lang import t

SPLASH_ART = r"""[bold green]
 ____                            _       _    _   _            _
| __ ) _   _ _ __ _   _ _ __   __| |_   _| | _| | | | __ _  ___| | __
|  _ \| | | | '__| | | | '_ \ / _` | | | | |/ / |_| |/ _` |/ __| |/ /
| |_) | |_| | |  | |_| | | | | (_| | |_| |   <|  _  | (_| | (__|   <
|____/ \__,_|_|   \__,_|_| |_|\__,_|\__,_|_|\_\_| |_|\__,_|\___|_|\_\
[/bold green]"""


def _box(text: str, style: str) -> str:
    inner = f"  {text}  "
    width = max(len(inner) + 4, 38)
    pad_total = width - len(inner) - 2
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    return f"""[{style}]
╔{'═' * width}╗
║{' ' * width}║
║{' ' * pad_left} {inner} {' ' * pad_right}║
║{' ' * width}║
╚{'═' * width}╝
[/{style}]"""


def show_splash():
    console.print(SPLASH_ART)
    console.print(f"[dim white]              ═══ {t('banner.subtitle')} ═══[/dim white]")
    console.print(f"[dim cyan]                    {t('banner.edition')}[/dim cyan]")
    console.print()


def show_access_granted(host: str = ""):
    console.print(_box(f"█ {t('banner.access_granted')} █", "bold green"))
    if host:
        console.print_success(t("banner.shell_obtained", host=f"[bold]{host}[/bold]"))


def show_access_denied(reason: str = ""):
    console.print(_box(f"✖ {t('banner.access_denied')} ✖", "bold red"))
    if reason:
        console.print_error(reason)


def show_mission_complete(title: str, rewards: dict):
    console.print(_box(f"★ {t('banner.mission_complete')} ★", "bold bright_yellow"))
    console.print(f"  [bold bright_white]{title}[/bold bright_white]")
    console.print()
    if rewards.get("reputation"):
        console.print(f"  [cyan]{t('banner.reputation')}:[/cyan] +{rewards['reputation']}")
    if rewards.get("unlock_tools"):
        tools = ", ".join(rewards["unlock_tools"])
        console.print(f"  [cyan]{t('banner.tools_unlocked')}:[/cyan] {tools}")
    console.print()


def show_mission_briefing(title: str, briefing: str, objectives: list):
    console.print()
    console.print_panel(
        f"{t('banner.mission_briefing')}: {title}",
        briefing,
        style="bright_yellow"
    )
    console.print()
    console.print(f"[bold cyan]{t('banner.objectives')}:[/bold cyan]")
    for i, obj in enumerate(objectives, 1):
        status = "[green]✓[/green]" if obj.completed else "[yellow]○[/yellow]"
        desc = obj.description
        if obj.completed:
            desc = f"[objective.done]{desc}[/objective.done]"
        else:
            desc = f"[objective.pending]{desc}[/objective.pending]"
        console.print(f"  {status} {i}. {desc}")
    console.print()
