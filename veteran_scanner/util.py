"""Utilitários: caminhos do sistema, sanitização de dados pessoais, varredura limitada e severidades."""

from __future__ import annotations

import datetime as _dt
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

IS_WINDOWS = os.name == "nt"

SEVERITIES = ["info", "low", "medium", "high", "critical"]
SEVERITY_SCORE = {"info": 0, "low": 1, "medium": 3, "high": 6, "critical": 10}
SEVERITY_LABEL = {
    "info": "INFO",
    "low": "BAIXA",
    "medium": "MÉDIA",
    "high": "ALTA",
    "critical": "CRÍTICA",
}


def lower_severity(sev: str) -> str:
    idx = SEVERITIES.index(sev)
    return SEVERITIES[max(0, idx - 1)]


def valid_severity(sev: str, default: str = "low") -> str:
    return sev if sev in SEVERITIES else default


def iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    try:
        return _dt.datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return None


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def filetime_to_epoch(ft: int) -> Optional[float]:
    """Converte FILETIME do Windows (intervalos de 100ns desde 1601) para epoch."""
    if not ft:
        return None
    ts = (ft - 116444736000000000) / 10_000_000
    if ts <= 0 or ts > 4102444800:  # depois de 2100 = valor inválido
        return None
    return ts


def file_times(path: Path) -> Tuple[Optional[float], Optional[float]]:
    """Retorna (criação/metadata, modificação). No Windows st_ctime é a data de criação."""
    try:
        st = path.stat()
    except OSError:
        return None, None
    return st.st_ctime, st.st_mtime


def newest(*values: Optional[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return max(vals) if vals else None


@dataclass
class Env:
    """Pastas do sistema que o scanner inspeciona. Pode ser simulado (--root) para testes."""

    local_appdata: Optional[Path]
    appdata: Optional[Path]
    userprofile: Optional[Path]
    temp: Optional[Path]
    windir: Optional[Path]
    program_files: List[Path] = field(default_factory=list)
    drives: List[Path] = field(default_factory=list)
    simulated: bool = False

    @classmethod
    def from_system(cls) -> "Env":
        def p(var: str) -> Optional[Path]:
            v = os.environ.get(var)
            return Path(v) if v else None

        pf = [x for x in (p("ProgramFiles"), p("ProgramFiles(x86)")) if x]
        return cls(
            local_appdata=p("LOCALAPPDATA"),
            appdata=p("APPDATA"),
            userprofile=p("USERPROFILE") or Path.home(),
            temp=p("TEMP"),
            windir=p("WINDIR") or (Path("C:/Windows") if IS_WINDOWS else None),
            program_files=pf,
            drives=[Path(f"{c}:\\") for c in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.isdir(f"{c}:\\")] if IS_WINDOWS else [],
        )

    @classmethod
    def from_root(cls, root: Path) -> "Env":
        """Layout de Windows falso dentro de `root` (usado em testes e demonstrações)."""
        root = Path(root)
        user = root / "Users" / "player"
        return cls(
            local_appdata=user / "AppData" / "Local",
            appdata=user / "AppData" / "Roaming",
            userprofile=user,
            temp=user / "AppData" / "Local" / "Temp",
            windir=root / "Windows",
            program_files=[root / "Program Files", root / "Program Files (x86)"],
            drives=[root],
            simulated=True,
        )

    def user_folders(self) -> List[Path]:
        """Downloads, Área de Trabalho e Documentos (incluindo variações do OneDrive)."""
        if not self.userprofile:
            return []
        base = self.userprofile
        names = ["Downloads", "Desktop", "Documents", "Área de Trabalho", "Documentos"]
        out = [base / n for n in names]
        try:
            for e in os.scandir(base):
                if e.is_dir() and e.name.lower().startswith("onedrive"):
                    out += [Path(e.path) / n for n in names]
        except OSError:
            pass
        seen, result = set(), []
        for p in out:
            key = str(p).lower()
            if key not in seen and p.is_dir():
                seen.add(key)
                result.append(p)
        return result


class Sanitizer:
    """Remove o nome de usuário do Windows dos caminhos antes de irem para o relatório."""

    def __init__(self, env: Env):
        self.prefix: Optional[str] = str(env.userprofile) if env.userprofile else None
        user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        if env.userprofile:
            user = env.userprofile.name or user
        self.username = user if len(user) >= 3 else ""

    def path(self, p) -> str:
        s = str(p)
        if self.prefix and s.lower().startswith(self.prefix.lower()):
            s = "%USERPROFILE%" + s[len(self.prefix):]
        if self.username:
            s = re.sub(re.escape(self.username), "<usuario>", s, flags=re.IGNORECASE)
        return s


DEFAULT_SKIP_DIRS = {
    "node_modules", ".git", "site-packages", "__pycache__", "packages", "microsoft",
    "google", "mozilla", "nvidia", "nvidia corporation", "steamapps", "cache", "caches",
    "windowsapps", "crashdumps", "d3dscache", "temp", "$recycle.bin",
}


def walk_limited(
    root: Path,
    max_depth: int,
    max_entries: int = 40000,
    skip_dirs: Optional[set] = None,
) -> Iterator[Tuple[os.DirEntry, int]]:
    """Percorre `root` até `max_depth` níveis, sem seguir links/junctions e com limite de entradas.

    Entradas diretamente em `root` têm profundidade 0.
    """
    skip = DEFAULT_SKIP_DIRS if skip_dirs is None else skip_dirs
    stack = [(Path(root), 0)]
    count = 0
    while stack:
        d, depth = stack.pop()
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            count += 1
            if count > max_entries:
                return
            yield e, depth
            try:
                is_dir = e.is_dir(follow_symlinks=False)
                if is_dir and (e.is_symlink() or (hasattr(e, "is_junction") and e.is_junction())):
                    is_dir = False
            except OSError:
                is_dir = False
            if is_dir and depth + 1 < max_depth and e.name.lower() not in skip:
                stack.append((Path(e.path), depth + 1))


def is_admin() -> bool:
    if not IS_WINDOWS:
        try:
            return os.geteuid() == 0  # type: ignore[attr-defined]
        except AttributeError:
            return False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False
