"""Allowlist oficial de Fast Flags do Roblox.

Desde 29/09/2025 o cliente do Roblox só aplica as Fast Flags locais que estão nesta lista;
o resto é ignorado. Baixamos a lista pública do CDN do Roblox (nenhum dado do jogador é enviado)
ou lemos um arquivo fornecido pelo organizador (--allowlist-file).
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Optional, Set, Tuple

ALLOWLIST_URL = "https://clientsettingscdn.roblox.com/v2/settings/secured-settings/PCDesktopClient"
FLAG_RE = re.compile(r"^[DS]?F(?:Flag|Int|String|Log)[A-Za-z0-9_]+$")
_PREFIX_RE = re.compile(r"^[DS]?F(?:Flag|Int|String|Log)")


def strip_prefix(name: str) -> str:
    return _PREFIX_RE.sub("", name).lower()


def extract_flag_names(obj) -> Set[str]:
    """Coleta recursivamente qualquer string (chave ou valor) com formato de Fast Flag.

    Não dependemos de um formato exato da resposta, que pode mudar.
    """
    found: Set[str] = set()
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if isinstance(k, str) and FLAG_RE.match(k):
                    found.add(k)
                stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, str) and FLAG_RE.match(cur):
            found.add(cur)
    return found


def normalized_set(names: Set[str]) -> Set[str]:
    """Comparamos pelo nome sem prefixo (FFlag/DFInt...) e em minúsculas."""
    return {strip_prefix(n) for n in names}


def fetch_online(timeout: float = 8.0) -> Tuple[Optional[Set[str]], str]:
    req = urllib.request.Request(ALLOWLIST_URL, headers={"User-Agent": "FairScan (scanner open source)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL fixa, HTTPS)
            data = json.loads(resp.read(5_000_000).decode("utf-8", errors="replace"))
    except Exception as ex:  # rede, TLS, JSON...
        return None, f"falha ao baixar ({type(ex).__name__})"
    names = extract_flag_names(data)
    if not names:
        return None, "resposta sem flags reconhecíveis"
    return names, "online (clientsettingscdn.roblox.com)"


def load_file(path: Path) -> Tuple[Optional[Set[str]], str]:
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as ex:
        return None, f"arquivo ilegível ({ex.__class__.__name__})"
    try:
        names = extract_flag_names(json.loads(text))
    except json.JSONDecodeError:
        # Também aceita um nome por linha
        names = {ln.strip() for ln in text.splitlines() if FLAG_RE.match(ln.strip())}
    if not names:
        return None, "arquivo sem flags reconhecíveis"
    return names, f"arquivo ({Path(path).name})"
