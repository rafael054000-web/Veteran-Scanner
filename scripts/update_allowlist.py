"""Baixa a allowlist oficial de Fast Flags e salva em veteran_scanner/data/allowlist.json.

Rodado pelo GitHub Actions (allowlist.yml). Se a resposta não tiver flags reconhecíveis,
mostra o início dela no log e não altera o arquivo.
"""

import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from veteran_scanner.allowlist import ALLOWLIST_URLS, extract_flag_names  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "veteran_scanner" / "data" / "allowlist.json"

for url in ALLOWLIST_URLS:
    print(f"GET {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Roblox/WinInet", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read(5_000_000).decode("utf-8", errors="replace")
            print(f"  HTTP {resp.status}, {len(body)} bytes")
    except Exception as ex:
        print(f"  falhou: {type(ex).__name__} {getattr(ex, 'code', '')}")
        continue
    try:
        names = extract_flag_names(json.loads(body))
    except ValueError:
        names = set()
    if not names:
        print("  sem flags reconhecíveis. Início da resposta:")
        print("  " + body[:1500].replace("\n", " "))
        continue
    data = {
        "_comment": "Allowlist oficial de Fast Flags do Roblox. Atualizada automaticamente pelo workflow allowlist.yml. Não edite à mão.",
        "updated": dt.date.today().isoformat(),
        "source": url,
        "flags": sorted(names),
    }
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    old_flags = json.loads(old).get("flags") if old else None
    if old_flags == data["flags"]:
        print(f"  {len(names)} flags, sem mudanças.")
    else:
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  {len(names)} flags salvas em {OUT}.")
    sys.exit(0)

print("Nenhuma fonte retornou a allowlist.")
sys.exit(0)
