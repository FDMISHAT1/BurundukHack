from commands.registry import register
from ui.console import console
from ui.lang import t


@register("osint", "cmd.osint.help", required_tool="osint")
def handle_osint(game, args):
    console.print_error(t("registry.tool_locked", cmd="osint"))


@register("phish", "cmd.phish.help", required_tool="phish")
def handle_phish(game, args):
    console.print_error(t("registry.tool_locked", cmd="phish"))
