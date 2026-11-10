"""Testes com uma árvore de Windows simulada. Rodam em qualquer sistema:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from veteran_scanner import allowlist as al  # noqa: E402
from veteran_scanner.checks import fflags, filesystem, logs, prefetch, processes, recent, registry, roblox_install  # noqa: E402
from veteran_scanner.checks.base import Context  # noqa: E402
from veteran_scanner.cli import main  # noqa: E402
from veteran_scanner.report import build_report, verify_report  # noqa: E402
from veteran_scanner.signatures import load_flag_rules, load_rules, load_signatures, normalize  # noqa: E402
from veteran_scanner.util import Env, Sanitizer  # noqa: E402

VERSION = "version-0123456789abcdef"


def touch(path: Path, content: str = "", mtime: float = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="veteran_test_"))
        self.env = Env.from_root(self.tmp)
        self.roblox = self.env.local_appdata / "Roblox"
        touch(self.roblox / "Versions" / VERSION / "RobloxPlayerBeta.exe", "x")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ctx(self, allow=None, since=None, rules=None):
        r = load_rules()
        if rules:
            r.update(rules)
        return Context(
            env=self.env, sanitize=Sanitizer(self.env), signatures=load_signatures(),
            flag_rules=load_flag_rules(), rules=r,
            allowlist=al.normalized_set(allow) if allow is not None else None,
            allowlist_source="teste" if allow is not None else "indisponível", since=since,
        )

    @staticmethod
    def sevs(result):
        return sorted(f.severity for f in result.findings)


class TestMatching(Base):
    def test_normalize(self):
        self.assertEqual(normalize("Synapse X.exe"), "synapsex")
        self.assertEqual(normalize("SOLARA.EXE-1A2B3C4D.pf"), "solara")
        self.assertEqual(normalize("wave (1).zip"), "wave")
        self.assertEqual(normalize("solara.zip.lnk"), "solara")

    def test_true_positives(self):
        db = load_signatures()
        for name in ["Solara.exe", "solara_v3.zip", "KRNL", "Fluxus-setup.exe", "SOLARA.EXE-1A2B3C4D.pf",
                     "Synapse X", "Xeno.exe", "cheatengine-x86_64.exe", "MyDllInjector.exe"]:
            self.assertIsNotNone(db.match(name), name)

    def test_no_false_positives(self):
        db = load_signatures()
        for name in ["Waves", "WaveBrowser", "Waves MaxxAudio", "Roblox", "RobloxPlayerBeta.exe", "Discord",
                     "solarized-theme", "krnlx_backup_old_notes", "steam.exe", "chrome.exe", "OBS"]:
            self.assertIsNone(db.match(name), name)


class TestFFlags(Base):
    def write_flags(self, data, where=None):
        where = where or (self.roblox / "Versions" / VERSION / "ClientSettings" / "ClientAppSettings.json")
        touch(where, json.dumps(data))

    def test_no_file(self):
        r = fflags.run(self.ctx(allow=set()))
        self.assertEqual(r.findings, [])

    def test_allowlist_classification(self):
        self.write_flags({"FFlagDebugGraphicsPreferOpenGL": "True", "FIntSomethingRandom": "5"})
        r = fflags.run(self.ctx(allow={"FFlagDebugGraphicsPreferOpenGL"}))
        titles = " | ".join(f.title for f in r.findings)
        self.assertIn("1 Fast Flag(s) fora da allowlist", titles)
        self.assertIn("1 Fast Flag(s) permitida(s)", titles)
        self.assertEqual(self.sevs(r), ["info", "low"])

    def test_known_abuse_flag_in_bloxstrap(self):
        path = self.env.local_appdata / "Bloxstrap" / "Modifications" / "ClientSettings" / "ClientAppSettings.json"
        self.write_flags({"DFIntS2PhysicsSenderRate": "1"}, path)
        r = fflags.run(self.ctx(allow={"FFlagDebugGraphicsPreferOpenGL"}))
        self.assertIn("high", self.sevs(r))
        abuse = [f for f in r.findings if f.severity == "high"][0]
        self.assertIn("NÃO está na allowlist", abuse.detail)
        self.assertTrue(abuse.evidence["arquivo"].startswith("%USERPROFILE%"))

    def test_unknown_allowlist(self):
        self.write_flags({"FIntFoo": "1"})
        r = fflags.run(self.ctx(allow=None))
        self.assertIn("efeito não verificado", r.findings[0].title)

    def test_malformed(self):
        touch(self.roblox / "Versions" / VERSION / "ClientSettings" / "ClientAppSettings.json", "{ not json")
        r = fflags.run(self.ctx(allow=set()))
        self.assertIn("malformado", r.findings[0].title)

    def test_extract_allowlist_shapes(self):
        self.assertEqual(al.extract_flag_names({"securedSettings": ["FFlagA", "DFIntB", "not a flag"]}), {"FFlagA", "DFIntB"})
        self.assertEqual(al.extract_flag_names({"applicationSettings": {"FStringC": "x"}}), {"FStringC"})


class TestFilesystem(Base):
    def test_executor_in_downloads(self):
        touch(self.env.userprofile / "Downloads" / "Solara.zip", "x")
        touch(self.env.userprofile / "Downloads" / "homework.pdf", "x")
        r = filesystem.run(self.ctx())
        self.assertEqual(len(r.findings), 1)
        self.assertEqual(r.findings[0].severity, "high")

    def test_executor_layout(self):
        d = self.env.userprofile / "Desktop" / "coisas"
        (d / "autoexec").mkdir(parents=True)
        (d / "workspace").mkdir()
        r = filesystem.run(self.ctx())
        self.assertTrue(any("Estrutura de pastas" in f.title for f in r.findings))

    def test_medium_confidence_is_downgraded(self):
        (self.env.local_appdata / "Wave").mkdir(parents=True)
        r = filesystem.run(self.ctx())
        self.assertEqual(r.findings[0].severity, "medium")

    def test_since_downgrade(self):
        old = time.time() - 90 * 86400
        touch(self.env.userprofile / "Downloads" / "krnl.exe", "x", mtime=old)
        if os.name != "nt":
            os.utime(self.env.userprofile / "Downloads" / "krnl.exe", (old, old))
        r = filesystem.run(self.ctx(since=time.time() - 7 * 86400))
        f = r.findings[0]
        # No Linux o ctime não pode ser forjado; só valida quando o timestamp ficou antigo.
        if f.timestamp and f.timestamp < time.time() - 30 * 86400:
            self.assertTrue(f.before_window)
            self.assertEqual(f.severity, "medium")


class TestOtherChecks(Base):
    def test_proxy_dll(self):
        touch(self.roblox / "Versions" / VERSION / "dxgi.dll", "x")
        r = roblox_install.run(self.ctx())
        self.assertEqual(self.sevs(r), ["medium"])

    def test_prefetch(self):
        touch(self.env.windir / "Prefetch" / "XENO.EXE-1A2B3C4D.pf", "x")
        touch(self.env.windir / "Prefetch" / "CHROME.EXE-11111111.pf", "x")
        r = prefetch.run(self.ctx())
        self.assertEqual(len(r.findings), 1)

    def test_recent(self):
        touch(self.env.appdata / "Microsoft" / "Windows" / "Recent" / "Fluxus.lnk", "x")
        r = recent.run(self.ctx())
        self.assertEqual(len(r.findings), 1)

    def test_logs(self):
        touch(self.roblox / "logs" / "0.log", "2026-11-10 info ... loaded solara module ...")
        touch(self.roblox / "logs" / "1.log", "nothing here, mentions waves and solarized")
        r = logs.run(self.ctx())
        self.assertEqual(len(r.findings), 1)
        self.assertEqual(r.findings[0].evidence["termo"], "solara")

    def test_missing_logs(self):
        r = logs.run(self.ctx())
        self.assertIn("Nenhum log", r.findings[0].title)

    def test_processes(self):
        r = processes.run(self.ctx(), lister=lambda: ["explorer.exe", "Solara.exe", "AutoHotkey64.exe"])
        sev = {f.evidence["processo"]: f.severity for f in r.findings}
        self.assertEqual(sev["Solara.exe"], "critical")
        self.assertEqual(sev["AutoHotkey64.exe"], "medium")

    def test_registry(self):
        def collector(notes):
            return [("UserAssist", r"C:\Users\player\Downloads\Solara\Solara.exe", time.time()),
                    ("MuiCache", r"C:\Program Files\Discord\Discord.exe", None),
                    ("HKCU\\Software", "Bloxstrap", None)]
        r = registry.run(self.ctx(), collector=collector)
        self.assertEqual(sorted(f.evidence["assinatura"] for f in r.findings), ["bloxstrap", "solara"])
        self.assertNotIn("player", json.dumps([f.to_dict() for f in r.findings]))


class TestReport(Base):
    def test_integrity_and_tamper(self):
        touch(self.env.userprofile / "Downloads" / "krnl.exe", "x")
        results = [filesystem.run(self.ctx())]
        rep = build_report(results, player="Nick", event="Liga", consent={"accepted": True, "terms_version": "1.0",
                           "accepted_at": "x"}, since=None, admin=False, allowlist_source="t", allowlist_count=0,
                           versions={"signatures_version": "t"})
        self.assertEqual(rep["verdict"]["level"], "suspicious")
        ok, _ = verify_report(rep)
        self.assertTrue(ok)
        rep["checks"][0]["findings"] = []
        ok, _ = verify_report(rep)
        self.assertFalse(ok)


class TestCLI(Base):
    def answers(self, *items):
        it = iter(items)
        return lambda prompt="": next(it)

    def test_full_run_and_verify(self):
        touch(self.env.userprofile / "Downloads" / "Solara.zip", "x")
        out = self.tmp / "out"
        code = main(["--root", str(self.tmp), "--offline", "--no-color", "--output", str(out)],
                    input_fn=self.answers("ACEITO", "s", "Nick", "Liga Teste", "s"))
        self.assertEqual(code, 2)
        reports = list(out.glob("*.json"))
        self.assertEqual(len(reports), 1)
        self.assertEqual(len(list(out.glob("*.txt"))), 1)
        data = json.loads(reports[0].read_text(encoding="utf-8"))
        self.assertEqual(data["player"], "Nick")
        self.assertEqual(main(["verify", str(reports[0]), "--no-color", "--code", data["integrity"]["code"]]), 0)

    def test_clean_machine(self):
        touch(self.roblox / "logs" / "0.log", "ok")
        out = self.tmp / "out"
        code = main(["--root", str(self.tmp), "--offline", "--no-color", "--output", str(out), "--player", "Nick",
                     "--event", "Liga"], input_fn=self.answers("ACEITO", "s", "n"))
        self.assertEqual(code, 0)
        self.assertEqual(list(out.glob("*")) if out.exists() else [], [])

    def test_declined(self):
        code = main(["--root", str(self.tmp), "--offline", "--no-color"], input_fn=self.answers("nao"))
        self.assertEqual(code, 4)

    def test_minor_without_guardian(self):
        code = main(["--root", str(self.tmp), "--offline", "--no-color"], input_fn=self.answers("ACEITO", "n", "n"))
        self.assertEqual(code, 4)


if __name__ == "__main__":
    unittest.main()
