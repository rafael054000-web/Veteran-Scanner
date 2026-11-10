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


ALLOWLIST_URLS = [ALLOWLIST_URL]
# Cópia atualizada diariamente pelo GitHub Actions (workflow allowlist.yml)
MIRROR_URL = "https://raw.githubusercontent.com/rafael054000-web/Veteran-Scanner/main/veteran_scanner/data/allowlist.json"
BUNDLED = Path(__file__).parent / "data" / "allowlist.json"


def _get_json(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"User-Agent": "Roblox/WinInet", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URLs fixas, HTTPS)
        return json.loads(resp.read(5_000_000).decode("utf-8", errors="replace"))


def _describe(ex: Exception) -> str:
    code = getattr(ex, "code", None)
    return f"{type(ex).__name__} {code}" if code else type(ex).__name__


def fetch_online(timeout: float = 8.0) -> Tuple[Optional[Set[str]], str]:
    """Tenta o Roblox e, se falhar, a cópia do repositório. Retorna (flags, descrição da fonte)."""
    errors = []
    for url in ALLOWLIST_URLS:
        try:
            names = extract_flag_names(_get_json(url, timeout))
        except Exception as ex:  # rede, TLS, HTTP, JSON...
            errors.append(_describe(ex))
            continue
        if names:
            return names, "online (Roblox)"
        errors.append("sem flags reconhecíveis")
    try:
        data = _get_json(MIRROR_URL, timeout)
        names = extract_flag_names(data)
        if names:
            return names, f"cópia do repositório (atualizada em {data.get('updated', '?')})"
        errors.append("cópia do repositório vazia")
    except Exception as ex:
        errors.append("cópia: " + _describe(ex))
    names, src = load_bundled()
    if names:
        return names, src + " — Roblox indisponível"
    return None, "falha ao baixar (" + "; ".join(errors) + ")"


def load_bundled() -> Tuple[Optional[Set[str]], str]:
    try:
        data = json.loads(BUNDLED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "cópia embutida ilegível"
    names = extract_flag_names(data)
    if not names:
        return None, "cópia embutida vazia"
    return names, f"cópia embutida (atualizada em {data.get('updated', '?')})"


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
