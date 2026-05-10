import sys
from rich.console import Console
from rich.theme import Theme

_theme = Theme({
    "info": "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "stage": "bold magenta",
    "dim": "dim white",
})

# Force UTF-8 output on Windows to handle Unicode characters
console = Console(theme=_theme, highlight=False)


def info(msg: str) -> None:
    console.print(f"[info]i[/info]  {msg}")


def success(msg: str) -> None:
    console.print(f"[success]OK[/success]  {msg}")


def warning(msg: str) -> None:
    console.print(f"[warning]![/warning]  {msg}")


def error(msg: str) -> None:
    console.print(f"[error]ERR[/error]  {msg}")


def stage(n: int, name: str) -> None:
    console.rule(f"[stage]Stage {n}: {name}[/stage]")


def dim(msg: str) -> None:
    console.print(f"[dim]{msg}[/dim]")
