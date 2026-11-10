# Copyright 2026 Fisioimagem / Antigravity Sovereign Omni-Fleet Extension
# Zero-Secret Runtime Key Binder & Zero-Key Local Tooling (DLP = 0)
"""Runtime 0600 Vault Key Binder and Zero-Key Local Tooling for Antigravity SDK.

Priority Chain (as mandated by Bruno):
  1. openai      (OpenAI Business Pro / Codex Pool + Loopback :3080/v1)
  2. google      (Google AI Ultra Gemini QuotaGuard Pool + Vertex)
  3. openrouter  (OpenRouter 6-Key Sharded Pool :8348/v1 + Weekly Pool)
  4. codecode    (OpenCode / CodeGPT / Foundry :8346/v1 Pool)
  5. huggingface (Hugging Face Pro Pool + Loopback SGLang :30000/v1)
  6. llama_local (Zero-cost Metal 4 Ollama :11434 + 5X Workstation :8266)
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

VAULT_DIR = pathlib.Path("/Users/brunopimentel/.neurochat-vault")

DLP_SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}|ghp_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|EAA[A-Za-z0-9]{20,}|pn_[A-Za-z0-9_-]{16,}|"
    r"rpa_[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{20,}|whsec_[A-Za-z0-9_-]{16,})"
)

PRIORITY_ORDER: tuple[str, ...] = (
    "openai",
    "google",
    "openrouter",
    "codecode",
    "huggingface",
    "llama_local",
)

PROVIDER_ENDPOINTS: dict[str, dict[str, Any]] = {
    "openai": {
        "gateway_url": "http://127.0.0.1:3080/v1",
        "direct_url": "https://api.openai.com/v1",
        "default_model": "gpt-5.4-mini",
        "env_var": "OPENAI_API_KEY",
        "vault_ref": "sovereign_6providers_10plus_active_and_archive_0600.json#openai.active",
    },
    "google": {
        "gateway_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "direct_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.5-flash",
        "sdk_default_model": "gemini-3.6-flash",
        "env_var": "GEMINI_API_KEY",
        "vault_ref": "sovereign_6providers_10plus_active_and_archive_0600.json#google_ai_studio_gemini.active_daily_quota_rotator",
    },
    "openrouter": {
        "gateway_url": "http://127.0.0.1:8348/v1",
        "direct_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-5.4-mini",
        "env_var": "OPENROUTER_API_KEY",
        "vault_ref": "openrouter_keys_pool_0600.json#SLOT_01..06",
    },
    "codecode": {
        "gateway_url": "http://127.0.0.1:8346/v1",
        "direct_url": "http://127.0.0.1:3080/v1",
        "default_model": "gpt-5.4-mini",
        "env_var": "OPENCODE_API_KEY",
        "vault_ref": "opencode_api_keys_pool.json#keys",
    },
    "huggingface": {
        "gateway_url": "http://127.0.0.1:30000/v1",
        "direct_url": "https://router.huggingface.co/v1",
        "default_model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "env_var": "HF_TOKEN",
        "vault_ref": "sovereign_6providers_10plus_active_and_archive_0600.json#huggingface.active",
    },
    "llama_local": {
        "gateway_url": "http://127.0.0.1:11434/v1",
        "workstation_5x_url": "http://127.0.0.1:8266",
        "default_model": "llama3.2:1b",
        "env_var": "OLLAMA_API_KEY",
        "vault_ref": "sovereign_6providers_10plus_active_and_archive_0600.json#ollama_llama_fallback_and_cloud.active",
    },
}


def redact_dlp(text: str) -> str:
    """Redacts any secret token pattern from strings (`DLP = 0`)."""
    if not text:
        return ""
    return DLP_SECRET_RE.sub("[REDACTED_DLP]", text)


def _fp12(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]


class VaultProviderKeyBinder:
    """Loads provider keys strictly in-memory from 0600 vault files."""

    def __init__(self, vault_dir: pathlib.Path = VAULT_DIR) -> None:
        self._vault_dir = vault_dir
        self._pools: dict[str, list[str]] = {p: [] for p in PRIORITY_ORDER}
        self._rr_cursor: dict[str, int] = {p: 0 for p in PRIORITY_ORDER}
        self.reload_pools()

    def _read_json_safe(self, filename: str) -> dict[str, Any]:
        p = self._vault_dir / filename
        if not p.is_file():
            return {}
        try:
            data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _clean_list(items: Any) -> list[str]:
        if not isinstance(items, list):
            return []
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            val = ""
            if isinstance(item, str):
                val = item.strip()
            elif isinstance(item, dict):
                val = str(item.get("key") or item.get("api_key") or item.get("token") or "").strip()
            if val and len(val) >= 12 and val not in seen:
                seen.add(val)
                out.append(val)
        return out

    def reload_pools(self) -> None:
        """Reloads in-memory key lists from sanctioned 0600 vault files."""
        s6 = self._read_json_safe("sovereign_6providers_10plus_active_and_archive_0600.json")
        aq4 = self._read_json_safe("aq4_multi_provider_key_pool.json").get("pools", {})
        oc = self._read_json_safe("opencode_api_keys_pool.json")
        cg = self._read_json_safe("codegpt_agent_e6238ca7.json")
        or_w = self._read_json_safe("openrouter_4keys_25usd_weekly_pool_0600.json")

        openai_keys = self._clean_list((s6.get("openai") or {}).get("active")) + self._clean_list(
            aq4.get("openai_codex")
        )
        google_keys = self._clean_list(
            (s6.get("google_ai_studio_gemini") or {}).get("active_daily_quota_rotator")
        ) + self._clean_list(aq4.get("google_gemini"))

        or_keys: list[str] = []
        for k_field in ("keys", "active_keys", "slots"):
            or_keys.extend(self._clean_list(or_w.get(k_field)))
        env_or = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if env_or:
            or_keys.insert(0, env_or)
        if not or_keys:
            or_keys.append("loopback-gateway-8348-managed-6keys")

        code_keys = self._clean_list(oc.get("keys")) + self._clean_list(aq4.get("opencode_platform"))
        if isinstance(cg.get("api_key"), str) and len(cg["api_key"].strip()) >= 12:
            code_keys.append(cg["api_key"].strip())
        if not code_keys and openai_keys:
            code_keys.append("loopback-gateway-8346-managed-foundry")

        hf_keys = self._clean_list((s6.get("huggingface") or {}).get("active")) + self._clean_list(
            aq4.get("huggingface_pro")
        )
        llama_keys = self._clean_list(
            (s6.get("ollama_llama_fallback_and_cloud") or {}).get("active")
        ) + self._clean_list(aq4.get("ollama_cloud"))
        if not llama_keys:
            llama_keys.append("ollama-local-metal4-zero-key")

        self._pools["openai"] = list(dict.fromkeys(openai_keys))
        self._pools["google"] = list(dict.fromkeys(google_keys))
        self._pools["openrouter"] = list(dict.fromkeys(or_keys))
        self._pools["codecode"] = list(dict.fromkeys(code_keys))
        self._pools["huggingface"] = list(dict.fromkeys(hf_keys))
        self._pools["llama_local"] = list(dict.fromkeys(llama_keys))

    def next_key(self, provider: str) -> tuple[str, str]:
        """Returns (resolved_provider, key) following Bruno's strict preference order."""
        chain = [provider] if provider in self._pools else []
        for p in PRIORITY_ORDER:
            if p not in chain:
                chain.append(p)
        for cand in chain:
            pool = self._pools.get(cand) or []
            if pool:
                idx = self._rr_cursor[cand] % len(pool)
                self._rr_cursor[cand] += 1
                return cand, pool[idx]
        return "openai", "loopback-gateway-3080-managed"

    def sanitized_telemetry(self) -> dict[str, Any]:
        """Returns DLP-safe pool telemetry (zero secret characters exposed)."""
        summary: dict[str, Any] = {}
        for p in PRIORITY_ORDER:
            pool = self._pools.get(p) or []
            meta = PROVIDER_ENDPOINTS[p]
            summary[p] = {
                "ready": len(pool) > 0,
                "pool_count": len(pool),
                "primary_slot_fp12": _fp12(pool[0]) if pool else None,
                "gateway_url": meta["gateway_url"],
                "default_model": meta["default_model"],
                "vault_ref": meta["vault_ref"],
            }
        return {
            "dlp_leaks": 0,
            "priority_order": list(PRIORITY_ORDER),
            "providers": summary,
        }

    def resolve_agent_binding(
        self,
        agent_name: str,
        preferred_provider: str | None = None,
        zero_key_local_capable: bool = False,
    ) -> dict[str, Any]:
        """Determines exact provider + vault reference + model binding for any agent."""
        low = agent_name.lower()
        pref = (preferred_provider or "").lower().strip()
        if not pref:
            if any(x in low for x in ("gemini", "google", "dak-", "vertex", "flutter", "firebase")):
                pref = "google"
            elif any(x in low for x in ("openrouter", "nemotron", "maverick", "qwen3-coder", "sonnet46", "opus46")):
                pref = "openrouter"
            elif any(x in low for x in ("opencode", "claude", "cowork", "foundry", "codegpt", "fable")):
                pref = "codecode"
            elif any(x in low for x in ("hf-", "huggingface", "sglang")):
                pref = "huggingface"
            elif zero_key_local_capable and any(
                x in low for x in ("metal4", "local", "sentinela", "sub-ast", "sub-clean")
            ):
                pref = "llama_local"
            else:
                pref = "openai"

        resolved_prov, key = self.next_key(pref)
        meta = PROVIDER_ENDPOINTS[resolved_prov]
        fallback_chain = [p for p in PRIORITY_ORDER if p != resolved_prov]
        return {
            "agent_name": agent_name,
            "zero_key_local_capable": zero_key_local_capable,
            "resolved_provider": resolved_prov,
            "fallback_priority_chain": fallback_chain,
            "gateway_url": meta["gateway_url"],
            "default_model": meta["default_model"],
            "env_var": meta["env_var"],
            "vault_slot_ref": meta["vault_ref"],
            "bound_key_fp12": _fp12(key),
            "_in_memory_key": key,
        }

    def build_antigravity_sdk_config(
        self,
        agent_name: str,
        system_instructions: str,
        preferred_provider: str | None = None,
        zero_key_local_capable: bool = False,
        extra_tools: list[Callable[..., Any]] | None = None,
        subagents: list[Any] | None = None,
        workspaces: list[str] | None = None,
        skills_paths: list[str] | None = None,
    ) -> Any:
        """Builds a live `google.antigravity` AgentConfig compatible with both 0.1.7 and 0.1.8."""
        import google.antigravity as agy
        from google.antigravity import LocalAgentConfig, types
        from google.antigravity.hooks import policy

        binding = self.resolve_agent_binding(
            agent_name=agent_name,
            preferred_provider=preferred_provider,
            zero_key_local_capable=zero_key_local_capable,
        )
        tools_list: list[Callable[..., Any]] = list(ZERO_KEY_LOCAL_TOOLS)
        if extra_tools:
            for t in extra_tools:
                if t not in tools_list:
                    tools_list.append(t)

        ws = workspaces or ["/Users/brunopimentel/CODEX"]
        sk_paths = skills_paths or ["/Users/brunopimentel/.gemini/config/skills"]
        prov = binding["resolved_provider"]
        key = binding["_in_memory_key"]
        _, google_key = self.next_key("google")
        _, openai_key = self.next_key("openai")

        cap_fields = getattr(types.CapabilitiesConfig, "model_fields", {})
        if "enable_subagents" in cap_fields:
            caps = types.CapabilitiesConfig(enable_subagents=True)
        else:
            caps = types.CapabilitiesConfig(
                file_reads=True,
                file_writes=True,
                command_execution=True,
                subagents=True,
                mcp=True,
            )

        env_map = {
            "OPENAI_API_KEY": key if prov in ("openai", "openrouter", "codecode", "huggingface") else openai_key,
            "GEMINI_API_KEY": google_key,
            "GOOGLE_API_KEY": google_key,
            binding["env_var"]: key,
        }

        local_openai_cls = getattr(agy, "LocalOpenAIAgentConfig", None)
        if prov != "google" and local_openai_cls is not None:
            return local_openai_cls(
                base_url=binding["gateway_url"],
                model=binding["default_model"],
                env=env_map,
                system_instructions=system_instructions,
                capabilities=caps,
                tools=tools_list,
                policies=[policy.allow_all()],
                subagents=subagents or [],
                workspaces=ws,
                skills_paths=sk_paths,
            )

        cfg_kwargs: dict[str, Any] = {
            "api_key": google_key,
            "system_instructions": system_instructions,
            "capabilities": caps,
            "tools": tools_list,
            "policies": [policy.allow_all()],
            "subagents": subagents or [],
            "workspaces": ws,
            "skills_paths": sk_paths,
        }
        if "env" in getattr(LocalAgentConfig, "model_fields", {}):
            cfg_kwargs["env"] = env_map
        return LocalAgentConfig(**cfg_kwargs)


def ast_syntax_check(file_path: str) -> str:
    """Zero-key deterministic AST syntax & bad-raise validator for Python files."""
    p = pathlib.Path(file_path).expanduser().resolve()
    if not p.is_file():
        return json.dumps({"ok": False, "error": "file_not_found", "path": str(p)})
    src = p.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src, filename=str(p))
    except SyntaxError as exc:
        return json.dumps(
            {
                "ok": False,
                "error_kind": "parse-error",
                "line": exc.lineno,
                "offset": exc.offset,
                "msg": exc.msg,
            }
        )

    bad_raises: list[dict[str, Any]] = []
    bare_excepts: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            if isinstance(node.exc, ast.Constant) and not isinstance(node.exc.value, BaseException):
                bad_raises.append(
                    {
                        "line": node.lineno,
                        "error_kind": "bad-raise",
                        "detail": f"Cannot raise literal of type {type(node.exc.value).__name__}; must inherit from BaseException",
                    }
                )
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            bare_excepts.append(node.lineno)

    return json.dumps(
        {
            "ok": len(bad_raises) == 0,
            "path": str(p),
            "bad_raises": bad_raises,
            "bare_except_lines": bare_excepts,
        }
    )


def pyrefly_type_check(file_path: str) -> str:
    """Zero-key static type verification using Meta Pyrefly CLI (`pyrefly check`)."""
    pyrefly_bin = shutil.which("pyrefly")
    if not pyrefly_bin:
        return json.dumps({"ok": True, "skipped": "pyrefly_not_in_path"})
    proc = subprocess.run(
        [pyrefly_bin, "check", "--output-format", "json", file_path],
        check=False,
        capture_output=True,
        text=True,
        timeout=25,
    )
    out = (proc.stdout or proc.stderr or "").strip()
    return json.dumps(
        {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "diagnostics_preview": redact_dlp(out[:1500]),
        }
    )


def ruff_lint_check(file_path: str) -> str:
    """Zero-key fast Rust linter check via `ruff check`."""
    ruff_bin = shutil.which("ruff")
    if not ruff_bin:
        return json.dumps({"ok": True, "skipped": "ruff_not_in_path"})
    proc = subprocess.run(
        [ruff_bin, "check", "--output-format", "concise", file_path],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return json.dumps(
        {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "issues": redact_dlp((proc.stdout or "").strip()[:1500]),
        }
    )


def dlp_secret_scan(file_path: str) -> str:
    """Zero-key DLP secret scanner ensuring 0 leaked tokens before commit."""
    p = pathlib.Path(file_path).expanduser().resolve()
    if not p.is_file():
        return json.dumps({"ok": False, "error": "file_not_found"})
    raw = p.read_text(encoding="utf-8", errors="ignore")
    matches = DLP_SECRET_RE.findall(raw)
    return json.dumps(
        {
            "ok": len(matches) == 0,
            "dlp_leaks_count": len(matches),
            "path": str(p),
        }
    )


def local_ollama_metal_infer(prompt: str, model: str = "llama3.2:1b") -> str:
    """Zero-API-cost local Metal 4 Llama inference on loopback :11434."""
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt[:4000],
            "stream": False,
            "keep_alive": "5m",
            "options": {"temperature": 1.0, "num_predict": 512},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            doc = json.loads(resp.read().decode("utf-8", errors="replace"))
            return redact_dlp(str(doc.get("response", "")).strip())
    except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        return f"[local_ollama_unavailable: {type(exc).__name__}]"


def fleet_zero_token_health() -> str:
    """Zero-token deterministic loopback health probe across core sovereign ports."""
    ports = (3080, 8085, 8209, 8260, 8265, 8266, 8346, 8348, 11434, 18627)
    results: dict[str, int] = {}
    for port in ports:
        path = "/v1/models" if port == 3080 else ("/api/tags" if port == 11434 else "/health")
        if port == 8265:
            path = "/api/agents/catalog"
        elif port == 8266:
            path = "/api/agents/all"
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2.5) as r:
                results[str(port)] = r.status
        except urllib.error.HTTPError as he:
            results[str(port)] = he.code
        except (OSError, ValueError, urllib.error.URLError, TimeoutError):
            results[str(port)] = 0
    return json.dumps({"ok": results.get("3080") == 200, "ports": results})


ZERO_KEY_LOCAL_TOOLS: tuple[Callable[..., Any], ...] = (
    ast_syntax_check,
    pyrefly_type_check,
    ruff_lint_check,
    dlp_secret_scan,
    local_ollama_metal_infer,
    fleet_zero_token_health,
)
