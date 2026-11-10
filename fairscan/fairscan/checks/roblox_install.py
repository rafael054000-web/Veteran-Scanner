"""Instalação do Roblox: procura DLLs "proxy" (técnica comum de injeção) nas pastas de versão.

Só lista nomes de arquivos. Não abre, não altera e não executa nada do Roblox.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from ..util import file_times, iso, newest
from .base import CheckResult, Context

ID, LABEL = "roblox_install", "Instalação do Roblox"

# DLLs do sistema que o Windows carrega da pasta do programa antes da do sistema.
# Uma cópia delas dentro da pasta do Roblox costuma ser injeção ou overlay (ex.: ReShade).
PROXY_DLLS = {
    "dxgi.dll", "d3d9.dll", "d3d10.dll", "d3d11.dll", "d3d12.dll", "opengl32.dll",
    "version.dll", "winmm.dll", "winhttp.dll", "dinput8.dll", "dsound.dll",
    "xinput1_3.dll", "xinput1_4.dll", "wininet.dll", "iphlpapi.dll", "dbghelp.dll",
}
PLAYER_EXE = "robloxplayerbeta.exe"


def version_dirs(ctx: Context) -> List[Path]:
    env = ctx.env
    bases: List[Path] = []
    if env.local_appdata and env.local_appdata.is_dir():
        try:
            for e in os.scandir(env.local_appdata):
                n = e.name.lower()
                if e.is_dir() and (n == "roblox" or n.endswith("strap")):
                    bases.append(Path(e.path) / "Versions")
        except OSError:
            pass
    bases += [pf / "Roblox" / "Versions" for pf in env.program_files]
    out = []
    for b in bases:
        if not b.is_dir():
            continue
        try:
            for e in os.scandir(b):
                if e.is_dir() and (Path(e.path) / "RobloxPlayerBeta.exe").exists():
                    out.append(Path(e.path))
        except OSError:
            pass
    return out


def run(ctx: Context) -> CheckResult:
    res = CheckResult(ID, LABEL)
    dirs = version_dirs(ctx)
    res.stats = {"pastas_de_versao": [ctx.sanitize.path(d) for d in dirs]}
    if not dirs:
        res.status = "partial"
        res.note = "Nenhuma instalação do Roblox Player encontrada nos locais padrão."
        return res
    for d in dirs:
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            if n.lower() in PROXY_DLLS:
                p = d / n
                created, modified = file_times(p)
                res.findings.append(ctx.finding(
                    ID, ctx.rules.get("proxy_dll_severity", "medium"),
                    f"DLL proxy na pasta do Roblox: {n}",
                    "Essa DLL normalmente fica só no Windows. Uma cópia na pasta do jogo pode ser injeção "
                    "de código ou um overlay gráfico (ex.: ReShade). Confira com o jogador.",
                    {"caminho": ctx.sanitize.path(p), "criado": iso(created), "modificado": iso(modified)},
                    newest(created, modified)))
    return res
