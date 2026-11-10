"""Saída no terminal (cores ANSI, com fallback para texto simples)."""

from __future__ import annotations

import os
import sys

from .util import IS_WINDOWS, SEVERITY_LABEL

_COLORS = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "red": "\033[91m", "yellow": "\033[93m", "green": "\033[92m",
    "cyan": "\033[96m", "magenta": "\033[95m", "gray": "\033[90m",
}
SEV_COLOR = {"info": "gray", "low": "cyan", "medium": "yellow", "high": "red", "critical": "magenta"}


def _enable_windows_ansi() -> bool:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


class UI:
    def __init__(self, color: bool = True):
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
            except Exception:
                pass
        use = color and sys.stdout.isatty() and not os.environ.get("NO_COLOR")
        if use and IS_WINDOWS:
            use = _enable_windows_ansi()
        self.color = use

    def c(self, text: str, *styles: str) -> str:
        if not self.color:
            return text
        return "".join(_COLORS[s] for s in styles) + text + _COLORS["reset"]

    def clear(self) -> None:
        if sys.stdout.isatty():
            os.system("cls" if IS_WINDOWS else "clear")

    def set_title(self, title: str) -> None:
        if IS_WINDOWS:
            try:
                import ctypes

                ctypes.windll.kernel32.SetConsoleTitleW(title)  # type: ignore[attr-defined]
            except Exception:
                pass
        elif sys.stdout.isatty():
            sys.stdout.write(f"\033]0;{title}\007")

    def box(self, lines, width: int = 64, style: str = "yellow") -> None:
        """Caixa com bordas arredondadas. Cada linha: texto ou (texto, estilos...)."""
        inner = width - 4
        self.print(self.c("╭" + "─" * (width - 2) + "╮", style))
        for item in lines:
            text, styles = (item, ()) if isinstance(item, str) else (item[0], item[1:])
            text = text[:inner]
            pad = " " * (inner - len(text))
            self.print(self.c("│ ", style) + (self.c(text, *styles) if styles else text) + pad + self.c(" │", style))
        self.print(self.c("╰" + "─" * (width - 2) + "╯", style))

    def print(self, text: str = "") -> None:
        print(text, flush=True)

    def rule(self, char: str = "─", width: int = 64) -> None:
        self.print(self.c(char * width, "gray"))

    def title(self, text: str) -> None:
        self.print()
        self.print(self.c(text, "bold", "yellow"))
        self.rule()

    def sev(self, severity: str) -> str:
        label = f"[{SEVERITY_LABEL.get(severity, severity)}]"
        return self.c(label.ljust(9), "bold", SEV_COLOR.get(severity, "gray"))

    def ask(self, prompt: str, input_fn=input) -> str:
        try:
            return input_fn(self.c(prompt, "bold")).strip()
        except EOFError:
            return ""

    def yes_no(self, prompt: str, default: bool = False, input_fn=input) -> bool:
        suffix = " [S/n] " if default else " [s/N] "
        ans = self.ask(prompt + suffix, input_fn).lower()
        if not ans:
            return default
        return ans in ("s", "sim", "y", "yes")
