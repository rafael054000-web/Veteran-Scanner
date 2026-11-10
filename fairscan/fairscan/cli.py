"""Interface de linha de comando.

    python -m fairscan                 # escaneia (padrão)
    python -m fairscan scan --since 2026-11-01 --event "Copa X"
    python -m fairscan verify relatorio.json   # para organizadores
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

from . import __version__, allowlist as allowlist_mod
from .checks import ALL
from .checks.base import CheckResult, Context
from .consent import ask_consent
from .report import build_report, safe_filename, to_text, verify_report
from .signatures import load_flag_rules, load_rules, load_signatures
from .ui import UI
from .util import IS_WINDOWS, SEVERITIES, Env, Sanitizer, is_admin

EXIT_CLEAN, EXIT_ATTENTION, EXIT_SUSPICIOUS, EXIT_ERROR, EXIT_DECLINED = 0, 1, 2, 3, 4
LEVEL_EXIT = {"clean": EXIT_CLEAN, "attention": EXIT_ATTENTION, "suspicious": EXIT_SUSPICIOUS}
LEVEL_COLOR = {"clean": "green", "attention": "yellow", "suspicious": "red"}

BANNER = r"""
  ███████╗ █████╗ ██╗██████╗ ███████╗ ██████╗ █████╗ ███╗   ██╗
  ██╔════╝██╔══██╗██║██╔══██╗██╔════╝██╔════╝██╔══██╗████╗  ██║
  █████╗  ███████║██║██████╔╝███████╗██║     ███████║██╔██╗ ██║
  ██╔══╝  ██╔══██║██║██╔══██╗╚════██║██║     ██╔══██║██║╚██╗██║
  ██║     ██║  ██║██║██║  ██║███████║╚██████╗██║  ██║██║ ╚████║
  ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝"""


def parse_since(text: str) -> float:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return _dt.datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError("data inválida; use AAAA-MM-DD ou DD/MM/AAAA (opcionalmente com HH:MM)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fairscan", description="Scanner de integridade com consentimento para campeonatos de Roblox.")
    p.add_argument("--version", action="version", version=f"FairScan {__version__}")
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("scan", help="verifica este computador (padrão)")
    _scan_args(s)

    v = sub.add_parser("verify", help="(organizadores) confere a integridade de um relatório .json")
    v.add_argument("report", type=Path)
    v.add_argument("--code", help="código de verificação anotado durante a chamada (ex.: AB12-CD34)")
    v.add_argument("--no-color", action="store_true")

    sub.add_parser("signatures", help="lista as assinaturas e regras carregadas")
    sub.add_parser("fingerprint", help="mostra a impressão digital desta cópia do scanner")
    return p


def _scan_args(s: argparse.ArgumentParser) -> None:
    s.add_argument("--player", help="seu nick no campeonato")
    s.add_argument("--event", default="", help="nome do campeonato")
    s.add_argument("--since", type=parse_since, help="início do campeonato; achados mais antigos pesam menos (AAAA-MM-DD)")
    s.add_argument("--output", type=Path, default=Path("."), help="pasta onde salvar o relatório (padrão: atual)")
    s.add_argument("--offline", action="store_true", help="não baixa a allowlist oficial de Fast Flags")
    s.add_argument("--allowlist-file", type=Path, help="usa uma allowlist local (JSON ou um nome por linha)")
    s.add_argument("--rules", type=Path, help="regras do campeonato (JSON que sobrescreve data/rules.json)")
    s.add_argument("--signatures", type=Path, help="assinaturas extras (JSON no mesmo formato de data/signatures.json)")
    s.add_argument("--no-color", action="store_true")
    s.add_argument("--root", type=Path, help=argparse.SUPPRESS)  # árvore de Windows simulada (testes/demonstração)


def run_checks(ctx: Context, ui: UI) -> List[CheckResult]:
    results = []
    for mod in ALL:
        label = mod.LABEL
        ui.print(ui.c("  › ", "cyan") + label + ui.c(" …", "gray"))
        start = time.time()
        try:
            r = mod.run(ctx)
        except Exception as ex:  # uma verificação com erro não derruba as outras
            r = CheckResult(mod.ID, label, status="error", note=f"Erro inesperado: {type(ex).__name__}: {ex}")
        r.stats["duracao_s"] = round(time.time() - start, 2)
        status = {"ok": ui.c("ok", "green"), "partial": ui.c("parcial", "yellow"),
                  "skipped": ui.c("pulada", "gray"), "error": ui.c("erro", "red")}[r.status]
        extra = f" — {len(r.findings)} achado(s)" if r.findings else ""
        ui.print(f"    {status}{extra}" + (ui.c(f"  ({r.note})", "gray") if r.note else ""))
        results.append(r)
    return results


def print_summary(ui: UI, report: dict) -> None:
    v = report["verdict"]
    ui.title("Resumo")
    order = list(reversed(SEVERITIES))
    rows = []
    for chk in report["checks"]:
        for f in chk["findings"]:
            rows.append(f)
    rows.sort(key=lambda f: order.index(f["severity"]))
    shown = [f for f in rows if f["severity"] != "info"]
    if not shown:
        ui.print("  Nenhum achado acima do nível informativo.")
    for f in shown[:25]:
        old = ui.c(" (antes do período)", "gray") if f["before_window"] else ""
        ui.print(f"  {ui.sev(f['severity'])} {f['title']}{old}")
    if len(shown) > 25:
        ui.print(ui.c(f"  … e mais {len(shown) - 25} achado(s) no relatório completo.", "gray"))
    info = len(rows) - len(shown)
    if info:
        ui.print(ui.c(f"  ({info} item(ns) apenas informativo(s) no relatório completo)", "gray"))
    ui.print()
    ui.print("  Resultado: " + ui.c(v["label"], "bold", LEVEL_COLOR[v["level"]]))
    ui.print(ui.c("  Isto é um indício para análise humana, não uma acusação automática.", "gray"))


def cmd_scan(args, input_fn=input) -> int:
    ui = UI(color=not args.no_color)
    ui.print(ui.c(BANNER, "cyan"))
    ui.print(ui.c(f"  v{__version__} — scanner open source com consentimento para campeonatos de Roblox", "gray"))

    if args.root:
        env = Env.from_root(args.root)
        ui.print(ui.c(f"\n  MODO SIMULAÇÃO: usando a árvore em {args.root}", "yellow"))
    elif IS_WINDOWS:
        env = Env.from_system()
    else:
        ui.print(ui.c("\nEste scanner foi feito para Windows (onde o Roblox roda no PC).", "red"))
        return EXIT_ERROR

    consent = ask_consent(ui, input_fn)
    if consent is None:
        ui.print("\nVerificação cancelada. Nada foi lido.")
        return EXIT_DECLINED

    player = (args.player or "").strip()
    for _ in range(3):
        if player:
            break
        player = ui.ask("Seu nick no campeonato: ", input_fn)
    player = player or "jogador"
    event = args.event.strip() or ui.ask("Nome do campeonato (Enter para pular): ", input_fn)

    try:
        signatures = load_signatures(args.signatures)
        rules = load_rules(args.rules)
        flag_rules = load_flag_rules()
    except (OSError, ValueError) as ex:
        ui.print(ui.c(f"Erro ao carregar regras/assinaturas: {ex}", "red"))
        return EXIT_ERROR

    ui.title("Preparando")
    names, source = None, "desativada (--offline)"
    if args.allowlist_file:
        names, source = allowlist_mod.load_file(args.allowlist_file)
    elif not args.offline:
        ui.print("  Baixando a allowlist pública de Fast Flags do Roblox…")
        names, source = allowlist_mod.fetch_online()
    ui.print(f"  Allowlist: {source}" + (f" — {len(names)} flags" if names else ""))
    admin = is_admin() and not env.simulated
    if not admin and not env.simulated and IS_WINDOWS:
        ui.print(ui.c("  Dica: rodando como administrador o scanner também verifica Prefetch e BAM.", "gray"))

    ctx = Context(
        env=env,
        sanitize=Sanitizer(env),
        signatures=signatures,
        flag_rules=flag_rules,
        rules=rules,
        allowlist=allowlist_mod.normalized_set(names) if names else None,
        allowlist_source=source,
        since=args.since,
        admin=admin,
    )

    ui.title("Verificando (somente leitura)")
    results = run_checks(ctx, ui)

    report = build_report(
        results, player=player, event=event, consent=consent, since=args.since, admin=admin,
        allowlist_source=source, allowlist_count=len(names) if names else 0,
        versions={"signatures_version": signatures.version, "fflag_list_version": flag_rules.version,
                  "rules_version": str(rules.get("version", "?"))},
    )
    print_summary(ui, report)

    code = report["integrity"]["code"]
    ui.print()
    ui.print("  Código de verificação: " + ui.c(f" {code} ", "bold", "magenta"))
    ui.print(ui.c("  (se estiver em chamada com a organização, mostre este código na tela)", "gray"))
    ui.print()

    if ui.yes_no("Salvar o relatório nesta pasta para enviar à organização?", default=True, input_fn=input_fn):
        out_dir = args.output
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        base = out_dir / f"fairscan_{safe_filename(player)}_{stamp}"
        json_path, txt_path = base.with_suffix(".json"), base.with_suffix(".txt")
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path.write_text(to_text(report), encoding="utf-8")
        ui.print(ui.c("\n  Relatório salvo:", "green"))
        ui.print(f"    {json_path.resolve()}  (envie este para a organização)")
        ui.print(f"    {txt_path.resolve()}  (versão para leitura)")
    else:
        ui.print("  Relatório não salvo.")
    return LEVEL_EXIT[report["verdict"]["level"]]


def cmd_verify(args) -> int:
    ui = UI(color=not args.no_color)
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        ui.print(ui.c(f"Não foi possível ler o relatório: {ex}", "red"))
        return EXIT_ERROR
    ok, expected = verify_report(report)
    ui.title("Verificação de relatório")
    ui.print(f"  Jogador:     {report.get('player')}")
    ui.print(f"  Data:        {report.get('created_at')}")
    sc = report.get("scanner", {})
    ui.print(f"  Scanner:     v{sc.get('version')} ({sc.get('fingerprint_kind')})")
    ui.print(f"  Impressão:   {sc.get('fingerprint')}")
    ui.print(ui.c("               compare com o SHA256 publicado na página de releases do projeto", "gray"))
    ui.print(f"  Código:      {expected['code']}")
    result_ok = ok
    if args.code:
        match = args.code.strip().upper() == expected["code"]
        result_ok = result_ok and match
        ui.print("  Código informado: " + (ui.c("confere", "green") if match else ui.c("NÃO confere", "red")))
    ui.print("  Integridade: " + (ui.c("OK — o conteúdo não foi alterado depois de gerado", "green") if ok
                                  else ui.c("FALHOU — o arquivo foi editado depois de gerado", "red")))
    if not args.code:
        ui.print(ui.c("  Atenção: sem o código anotado durante a chamada, a integridade só detecta edições ingênuas.", "gray"))
    v = report.get("verdict", {})
    ui.print(f"  Resultado do scan: {v.get('label')}")
    return EXIT_CLEAN if result_ok else EXIT_ATTENTION


def cmd_signatures() -> int:
    ui = UI()
    db, rules, fr = load_signatures(), load_rules(), load_flag_rules()
    ui.title(f"Assinaturas (versão {db.version})")
    from .signatures import category_severity
    for s in db.signatures:
        sev = category_severity(rules, s.category, s.confidence)
        ui.print(f"  {ui.sev(sev)} {s.name:<32} {ui.c(s.category, 'gray')}")
    ui.title(f"Fast Flags associadas a abuso (versão {fr.version})")
    for name, reason in fr.known.items():
        ui.print(f"  {name}: {reason}")
    return EXIT_CLEAN


def main(argv: Optional[List[str]] = None, input_fn=input) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-") and argv[0] not in ("-h", "--help", "--version"):
        argv = ["scan"] + argv
    args = build_parser().parse_args(argv)
    try:
        if args.command == "verify":
            return cmd_verify(args)
        if args.command == "signatures":
            return cmd_signatures()
        if args.command == "fingerprint":
            from .report import scanner_fingerprint
            kind, fp = scanner_fingerprint()
            print(f"FairScan {__version__} ({kind}): {fp}")
            return EXIT_CLEAN
        return cmd_scan(args, input_fn)
    except KeyboardInterrupt:
        print("\nInterrompido.")
        return EXIT_ERROR
    except BrokenPipeError:
        return EXIT_CLEAN


def entry() -> None:
    code = main()
    if getattr(sys, "frozen", False):  # .exe aberto com duplo clique: não fechar a janela na hora
        try:
            input("\nPressione Enter para sair…")
        except EOFError:
            pass
    sys.exit(code)
