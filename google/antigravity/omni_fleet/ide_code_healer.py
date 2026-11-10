# Copyright 2026 Fisioimagem / Antigravity Sovereign Omni-Fleet Extension
"""Background IDE Code Auditor & Healer alongside Claude + Cowork + Llama."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import pathlib
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

from google.antigravity.omni_fleet.vault_key_binder import (
    VaultProviderKeyBinder,
    ast_syntax_check,
    dlp_secret_scan,
    local_ollama_metal_infer,
    pyrefly_type_check,
    redact_dlp,
    ruff_lint_check,
)

GUARDIAN_REGISTRY = pathlib.Path(
    "/Users/brunopimentel/CODEX/manifests/SOVEREIGN_IMMUTABLE_CONFIG_REGISTRY_SHA256.json"
)
_LOGGER = logging.getLogger(__name__)


def load_immutable_protected_paths() -> set[str]:
    """Loads the exact 55 guardian-locked paths so background healer never mutates them."""
    protected: set[str] = set()
    if GUARDIAN_REGISTRY.is_file():
        try:
            doc = json.loads(GUARDIAN_REGISTRY.read_text(encoding="utf-8", errors="ignore"))
            for item in doc.get("files", []):
                if isinstance(item, dict) and item.get("path"):
                    protected.add(str(pathlib.Path(item["path"]).resolve()))
        except (OSError, ValueError) as exc:
            _LOGGER.debug("Failed loading guardian registry: %s", type(exc).__name__)
    return protected


class BackgroundIdeCodeHealer:
    """Event-driven background IDE code auditor & cooperative Claude + Cowork + Llama healer."""

    def __init__(self, binder: VaultProviderKeyBinder | None = None) -> None:
        self.binder = binder or VaultProviderKeyBinder()
        self._mtime_cache: dict[str, float] = {}
        self._protected = load_immutable_protected_paths()

    def audit_file(self, file_path: str, invoke_council_on_issue: bool = True) -> dict[str, Any]:
        """Runs polyglot static & type checks + optional Claude/Cowork/Llama correction proposal."""
        p = pathlib.Path(file_path).expanduser().resolve()
        if not p.is_file():
            return {"ok": False, "error": "file_not_found", "path": str(p)}

        is_immutable = str(p) in self._protected
        suffix = p.suffix.lower()
        checks: dict[str, Any] = {
            "dlp": json.loads(dlp_secret_scan(str(p))),
        }
        has_error = not checks["dlp"].get("ok", True)

        if suffix == ".py":
            checks["ast"] = json.loads(ast_syntax_check(str(p)))
            checks["ruff"] = json.loads(ruff_lint_check(str(p)))
            checks["pyrefly"] = json.loads(pyrefly_type_check(str(p)))
            if not checks["ast"].get("ok", True) or not checks["ruff"].get("ok", True):
                has_error = True
        elif suffix in (".js", ".mjs", ".cjs"):
            node_bin = shutil.which("node")
            if node_bin:
                proc = subprocess.run(
                    [node_bin, "--check", str(p)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                checks["node_check"] = {
                    "ok": proc.returncode == 0,
                    "stderr": redact_dlp((proc.stderr or "")[:800]),
                }
                if proc.returncode != 0:
                    has_error = True
        elif suffix == ".swift":
            swiftc_bin = shutil.which("swiftc")
            if swiftc_bin:
                proc = subprocess.run(
                    [swiftc_bin, "-typecheck", str(p)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=25,
                )
                checks["swiftc_typecheck"] = {
                    "ok": proc.returncode == 0,
                    "stderr": redact_dlp((proc.stderr or "")[:800]),
                }
                if proc.returncode != 0:
                    has_error = True

        council_proposal: dict[str, Any] | None = None
        if has_error and invoke_council_on_issue:
            excerpt = redact_dlp(p.read_text(encoding="utf-8", errors="replace")[:3000])
            diag_json = json.dumps(checks, ensure_ascii=False)[:1500]
            council_proposal = self.consult_claude_cowork_llama_council(
                file_name=p.name,
                diagnostics_summary=diag_json,
                code_excerpt=excerpt,
            )

        return {
            "ok": not has_error,
            "path": str(p),
            "immutable_protected": is_immutable,
            "checks": checks,
            "claude_cowork_llama_council": council_proposal,
        }

    def consult_claude_cowork_llama_council(
        self,
        file_name: str,
        diagnostics_summary: str,
        code_excerpt: str,
    ) -> dict[str, Any]:
        """Runs parallel background code-fix synthesis across Antigravity(OpenAI/Google) + Claude/Cowork + Llama."""
        prompt = (
            f"Arquivo: {file_name}\n"
            f"Diagnósticos IDE (Pyrefly/Ruff/AST): {diagnostics_summary}\n"
            f"Trecho:\n{code_excerpt[:1800]}\n\n"
            "Forneça o diagnóstico raiz exato e a correção cirúrgica mínima em até 5 linhas."
        )

        def _claude_cowork_leg() -> dict[str, Any]:
            t0 = time.perf_counter()
            _, key = self.binder.next_key("codecode")
            body = {
                "model": "claude-sonnet-4-6",
                "messages": [
                    {
                        "role": "system",
                        "content": "Claude Code + Cowork Background IDE Surgeon. Corrija erros sem remover código funcional.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 220,
                "temperature": 1.0,
            }
            for url, hdr_key in (
                ("http://127.0.0.1:3080/v1/chat/completions", key),
                ("http://127.0.0.1:8348/v1/chat/completions", key),
            ):
                try:
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {hdr_key}"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=15) as r:
                        doc = json.loads(r.read().decode("utf-8", errors="replace"))
                        txt = (((doc.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                        if txt:
                            return {
                                "engine": "claude_cowork_ide",
                                "http_status": r.status,
                                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                                "advice": redact_dlp(txt[:500]),
                            }
                except (OSError, ValueError, urllib.error.URLError, TimeoutError):
                    continue
            return {"engine": "claude_cowork_ide", "http_status": 0, "advice": "standby"}

        def _llama_leg() -> dict[str, Any]:
            t0 = time.perf_counter()
            ans = local_ollama_metal_infer(prompt, model="llama3.2:1b")
            return {
                "engine": "llama_metal4_co_healer",
                "http_status": 200 if ans and not ans.startswith("[") else 0,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "advice": redact_dlp(ans[:500]),
            }

        def _antigravity_openai_google_leg() -> dict[str, Any]:
            t0 = time.perf_counter()
            _, oa_key = self.binder.next_key("openai")
            body = {
                "model": "gpt-5.4-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Antigravity IDE Background Verifier (OpenAI/Google Primary). Valide tipagem Pyrefly e AST.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 220,
                "temperature": 1.0,
            }
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:3080/v1/chat/completions",
                    data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {oa_key}"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    doc = json.loads(r.read().decode("utf-8", errors="replace"))
                    txt = (((doc.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                    return {
                        "engine": "antigravity_openai_google_verifier",
                        "http_status": r.status,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                        "advice": redact_dlp(txt[:500]),
                    }
            except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
                return {
                    "engine": "antigravity_openai_google_verifier",
                    "http_status": 0,
                    "advice": type(exc).__name__,
                }

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            f1 = pool.submit(_antigravity_openai_google_leg)
            f2 = pool.submit(_claude_cowork_leg)
            f3 = pool.submit(_llama_leg)
            legs = [f1.result(), f2.result(), f3.result()]

        return {
            "council_quorum_ok": sum(1 for x in legs if x["http_status"] == 200) >= 2,
            "members": legs,
        }

    def scan_changed_workspace_files(
        self,
        directories: list[str] | None = None,
        max_files_per_tick: int = 25,
    ) -> dict[str, Any]:
        """Scans only newly modified files (`mtime` delta) so idle CPU/API usage is zero."""
        dirs = directories or [
            "/Users/brunopimentel/CODEX/controllers",
            "/Users/brunopimentel/CODEX/antigravity_fusion",
            "/Users/brunopimentel/CODEX/antigravity_bridge",
        ]
        changed: list[pathlib.Path] = []
        for d_str in dirs:
            d = pathlib.Path(d_str)
            if not d.is_dir():
                continue
            for f in d.iterdir():
                if not f.is_file() or f.suffix.lower() not in (".py", ".js", ".mjs", ".swift"):
                    continue
                try:
                    mt = f.stat().st_mtime
                except OSError:
                    continue
                key = str(f)
                if self._mtime_cache.get(key) != mt:
                    self._mtime_cache[key] = mt
                    changed.append(f)

        audited: list[dict[str, Any]] = []
        for f in changed[:max_files_per_tick]:
            res = self.audit_file(str(f), invoke_council_on_issue=False)
            if not res["checks"].get("dlp", {}).get("ok", True) or (
                "ast" in res["checks"] and not res["checks"]["ast"].get("ok", True)
            ):
                res = self.audit_file(str(f), invoke_council_on_issue=True)
            audited.append(
                {
                    "file": f.name,
                    "ok": res["ok"],
                    "immutable_protected": res["immutable_protected"],
                    "ast_ok": res["checks"].get("ast", {}).get("ok", True),
                    "dlp_ok": res["checks"].get("dlp", {}).get("ok", True),
                    "council_invoked": res["claude_cowork_llama_council"] is not None,
                }
            )

        return {
            "scanned_changed_files": len(audited),
            "total_tracked_files": len(self._mtime_cache),
            "all_ast_and_dlp_clean": all(x["ast_ok"] and x["dlp_ok"] for x in audited),
            "results": audited,
        }
