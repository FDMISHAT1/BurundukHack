import time
import random
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from ui.console import console
from ui.lang import t


def fake_progress(description: str, seconds: float = 2.0, steps: int = 100):
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold green]{task.description}"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bold green"),
        TextColumn("[cyan]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console.console,
    ) as progress:
        task = progress.add_task(description, total=steps)
        for _ in range(steps):
            time.sleep(seconds / steps + random.uniform(0, seconds / steps / 2))
            progress.advance(task)


def typing_effect(text: str, delay: float = 0.03):
    for char in text:
        console.console.print(char, end="", highlight=False)
        time.sleep(delay)
    console.console.print()


def scan_animation(hosts_found: list[str], seconds: float = 3.0):
    console.print_info(t("anim.initiating_scan"))
    console.print()
    delay_per_host = seconds / max(len(hosts_found), 1)
    for ip in hosts_found:
        time.sleep(delay_per_host * random.uniform(0.5, 1.5))
        console.print(f"  [green]●[/green] {t('anim.discovered_host', ip=f'[bold cyan]{ip}[/bold cyan]')}")
    console.print()


def crack_animation(wordlist: list[str], target_password: str, seconds: float = 4.0):
    found = False
    total = len(wordlist)
    delay_per_word = seconds / max(total, 1)
    label = t("anim.cracking")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn(f"[bold green]{label}"),
        BarColumn(bar_width=30, complete_style="green"),
        TextColumn("[cyan]{task.percentage:>3.0f}%"),
        TextColumn("[dim]Trying: {task.fields[current_word]}[/dim]"),
        console=console.console,
    ) as progress:
        task = progress.add_task(label, total=total, current_word="...")

        for i, word in enumerate(wordlist):
            time.sleep(delay_per_word * random.uniform(0.3, 1.2))
            progress.update(task, advance=1, current_word=word)

            if word == target_password:
                found = True
                progress.update(task, completed=total, current_word=word)
                break

    return found


def exploit_animation(exploit_name: str, target: str, seconds: float = 3.0):
    console.print()
    console.print(f"[bold yellow]>> {t('anim.launching_exploit', name=exploit_name)}[/bold yellow]")
    console.print(f"[dim]{t('anim.target', target=target)}[/dim]")
    console.print()

    stages = [
        t("anim.stage_connect"),
        t("anim.stage_payload"),
        t("anim.stage_exploit"),
        t("anim.stage_backdoor"),
        t("anim.stage_shell"),
    ]
    delay_per_stage = seconds / len(stages)
    for stage in stages:
        time.sleep(delay_per_stage * random.uniform(0.7, 1.3))
        console.print(f"  [dim green]> {stage}[/dim green]")
    console.print()
