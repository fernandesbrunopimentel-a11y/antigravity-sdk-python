# Copyright 2026 Fisioimagem / Antigravity Sovereign Omni-Fleet Extension
"""Zero-Selection Automatic Squad Selector & Parallel Multi-Provider Dispatcher."""

from __future__ import annotations

import concurrent.futures
import json
import pathlib
import re
import time
import urllib.error
import urllib.request
from typing import Any

from google.antigravity.omni_fleet.vault_key_binder import (
    PROVIDER_ENDPOINTS,
    ZERO_KEY_LOCAL_TOOLS,
    VaultProviderKeyBinder,
    redact_dlp,
)

AGY_AGENTS_DIR = pathlib.Path("/Users/brunopimentel/.gemini/config/agents")
AGY_SKILLS_DIR = pathlib.Path("/Users/brunopimentel/.gemini/config/skills")
AGY_PLUGINS_DIR = pathlib.Path("/Users/brunopimentel/.gemini/config/plugins")
AGY_COMMANDS_DIR = pathlib.Path("/Users/brunopimentel/.gemini/config/commands")
VSCODE_EXT_DIR = pathlib.Path("/Users/brunopimentel/.antigravity/extensions")

DOMAIN_TAXONOMY: dict[str, dict[str, Any]] = {
    "code_ast_ide_correction": {
        "keywords": (
            "code", "codigo", "bug", "erro", "fix", "corrig", "pyrefly", "ruff",
            "lint", "ast", "type", "python", "ts", "js", "swift", "ide", "refactor",
            "syntax", "bad-raise", "test", "pytest", "benchmark", "claude", "cowork",
        ),
        "preferred_agents": (
            "agy-zh-01-bonsai2-rapid-architect",
            "agy-zh-03-claude-sonnet-4-6-verifier",
            "agy-zh-07-gpt-5-4-sovereign-coder",
            "opencli-healer-02-python-ruff-ast-surgeon",
            "sub-ast-001-python_ast_validator",
            "codefix-benchmark-agent",
            "llama-cadence-05-metal4-local-1b",
        ),
        "skills": ("google-antigravity-sdk", "systematic-debugging", "verification-before-completion"),
    },
    "github_git_devops_commit": {
        "keywords": (
            "git", "github", "commit", "push", "branch", "repo", "pr", "merge",
            "diff", "vscode", "workspace", "plugin", "sdk", "cli",
        ),
        "preferred_agents": (
            "cf-ag-11-edge-github-ast-sync",
            "jarvis-ag-04-codex53-surgeon",
            "opencode-git-precommit-dlp-enforcer",
            "sub-ast-019-hardcoded_secret_scanner",
            "agy-sess-12-openrouter-claude-opus46",
            "vscode-custom-agents-handoff-architect",
        ),
        "skills": ("git-workflows", "github-ssh-sync", "yeet"),
    },
    "neurochat_clinical_omnichannel": {
        "keywords": (
            "neurochat", "helena", "wts", "whatsapp", "waba", "zapi", "paciente",
            "tomografia", "216", "clinica", "fisioimagem", "laudo", "pacs", "bruno",
            "atendimento", "lead", "canal", "sessao",
        ),
        "preferred_agents": (
            "foundry-nc-01-bruno-intake-triage",
            "foundry-nc-02-imagem-tomografia-closer",
            "foundry-nc-12-waba-6827-cloudapi-master",
            "jarvis-ag-02-claude-fable-bypass",
            "llama-cadence-01-maverick-moe",
            "agy-sess-19-ollama-cloud-gptoss-120b",
        ),
        "skills": ("neurochat-superagent", "neurochat-enterprise-mirror-wts-sort", "stg-clinical-integration"),
    },
    "cloudflare_edge_queues_r2": {
        "keywords": (
            "cloudflare", "worker", "wrangler", "d1", "r2", "dlq", "queue",
            "edge", "waf", "206", "tunnel", "astra-24x7",
        ),
        "preferred_agents": (
            "cf-ag-01-edge-intake-fastpath",
            "cf-ag-02-edge-waf-access-shield",
            "cf-ag-05-edge-dlq-autohealer",
            "cf-ag-06-edge-distributed-brain",
            "opencode-cloudflare-worker-esm-packager",
            "jarvis-ag-17-cloudflare-wfp-queues-edge-sniper",
        ),
        "skills": ("agents-sdk", "cloudflare-deploy", "workers-best-practices"),
    },
    "meta_ads_readonly_governance": {
        "keywords": (
            "meta", "instagram", "facebook", "capi", "pixel", "ctwa", "roas",
            "anuncio", "campanha", "criativo",
        ),
        "preferred_agents": (
            "jarvis-ag-09-meta-ctwa-guardian",
            "meta-suite-01-graph-api-governor",
            "meta-suite-03-business-sdk-readonly",
            "manus-meta-04-ghost-legacy-ad-guard",
            "dotops-meta-auditor-v1",
        ),
        "skills": ("Creative Testing", "ROAS Optimization", "meta-campaign-sovereign-lock"),
    },
    "rag_memory_gdrive_32tb": {
        "keywords": (
            "rag", "faiss", "bm25", "drive", "32tb", "memoria", "memory",
            "vetor", "vector", "embedding", "conhecimento", "index",
        ),
        "preferred_agents": (
            "agy-sess-20-google-ultra-gemini31-flash",
            "jarvis-ag-07-gemini-ultra-drive-memory",
            "jarvis-ag-15-perpetual-memory-faiss-drive32tb",
            "cf-ag-07-edge-memory-15m-30days",
            "manus-meta-05-drive-vector-brain",
        ),
        "skills": ("gdrive", "cloudflare-neurochat-mcp-rag"),
    },
    "runpod_azure_realtime_cluster": {
        "keywords": (
            "runpod", "gpu", "pod", "serverless", "azure", "vm", "wss",
            "websocket", "socket", "ssh", "latencia", "p99", "cluster",
        ),
        "preferred_agents": (
            "jarvis-ag-10-runpod-elastic-governor",
            "jarvis-ag-12-supercluster-datacenter-engineer",
            "cf-ag-09-edge-runpod-serverless-min0",
            "agy-sess-06-azure-gpt6-astra-realtime",
            "main-eng-182-wss_streaming_low_latency",
        ),
        "skills": ("runpod", "azure-ai-gateway", "mac-supercluster-aug2-zero-loss-omni-ai"),
    },
}


def _parse_frontmatter(md_text: str) -> tuple[dict[str, Any], str]:
    """Lightweight, zero-dependency YAML frontmatter extractor."""
    if not md_text.startswith("---"):
        return {}, md_text.strip()
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}, md_text.strip()
    raw_fm, body = parts[1], parts[2].strip()
    meta: dict[str, Any] = {}
    for line in raw_fm.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "-")) or ":" not in s:
            continue
        k, v = s.split(":", 1)
        val = v.strip().strip("'\"")
        if val.lower() in ("true", "false"):
            meta[k.strip()] = val.lower() == "true"
        else:
            meta[k.strip()] = val
    return meta, body


class OmniSquadOrchestrator:
    """Master catalog & automatic squad selector inside Google Antigravity SDK."""

    def __init__(self, binder: VaultProviderKeyBinder | None = None) -> None:
        self.binder = binder or VaultProviderKeyBinder()
        self._agents_cache: dict[str, dict[str, Any]] = {}
        self.reload_catalog()

    def reload_catalog(self) -> dict[str, Any]:
        """Loads all consolidated Antigravity `.md` agents into fast memory index."""
        agents: dict[str, dict[str, Any]] = {}
        if AGY_AGENTS_DIR.is_dir():
            for md_file in sorted(AGY_AGENTS_DIR.glob("*.md")):
                try:
                    raw = md_file.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                fm, body = _parse_frontmatter(raw)
                name = str(fm.get("name") or md_file.stem).strip()
                desc = str(fm.get("description") or body[:180]).strip()
                zero_key = bool(
                    fm.get("zero_key_local_capable")
                    or any(
                        p in name.lower()
                        for p in (
                            "sub-ast-",
                            "sub-clean-",
                            "sub-probe-",
                            "sub-schema-",
                            "sub-synth-",
                            "opencli-healer-",
                            "sentinela",
                            "metal4-local",
                        )
                    )
                )
                pref_prov = str(fm.get("assigned_provider") or fm.get("preferred_provider") or "").strip() or None
                binding = self.binder.resolve_agent_binding(
                    agent_name=name,
                    preferred_provider=pref_prov,
                    zero_key_local_capable=zero_key,
                )
                agents[name] = {
                    "name": name,
                    "stem": md_file.stem,
                    "file": str(md_file),
                    "description": desc[:280],
                    "origin": str(fm.get("migrated_from") or "antigravity_native"),
                    "always_active": True,
                    "zero_key_local_capable": zero_key,
                    "resolved_provider": binding["resolved_provider"],
                    "gateway_url": binding["gateway_url"],
                    "default_model": binding["default_model"],
                    "vault_slot_ref": binding["vault_slot_ref"],
                    "instructions_excerpt": body[:1200] if body else desc,
                }
        self._agents_cache = agents
        return self.ecosystem_summary()

    def ecosystem_summary(self) -> dict[str, Any]:
        skills_cnt = sum(1 for x in AGY_SKILLS_DIR.iterdir() if x.is_dir()) if AGY_SKILLS_DIR.is_dir() else 0
        plugins_cnt = sum(1 for x in AGY_PLUGINS_DIR.iterdir() if x.is_dir()) if AGY_PLUGINS_DIR.is_dir() else 0
        cmds_cnt = sum(1 for x in AGY_COMMANDS_DIR.glob("*.md")) if AGY_COMMANDS_DIR.is_dir() else 0
        ext_cnt = sum(1 for x in VSCODE_EXT_DIR.iterdir() if x.is_dir()) if VSCODE_EXT_DIR.is_dir() else 0
        by_prov: dict[str, int] = {}
        by_origin: dict[str, int] = {}
        zero_key_cnt = 0
        for spec in self._agents_cache.values():
            p = spec["resolved_provider"]
            o = spec["origin"]
            by_prov[p] = by_prov.get(p, 0) + 1
            by_origin[o] = by_origin.get(o, 0) + 1
            if spec["zero_key_local_capable"]:
                zero_key_cnt += 1
        return {
            "total_unified_agents": len(self._agents_cache),
            "zero_key_local_agents": zero_key_cnt,
            "api_key_bound_agents": len(self._agents_cache) - zero_key_cnt,
            "agents_by_provider": by_prov,
            "agents_by_origin": by_origin,
            "active_skills_count": skills_cnt,
            "active_plugins_count": plugins_cnt,
            "active_slash_commands_count": cmds_cnt,
            "active_ide_vscode_extensions_count": ext_cnt,
            "manual_selection_required": False,
            "auto_squad_mode": "PERPETUAL_ALWAYS_ACTIVE_MAX_PERFORMANCE",
            "vault_telemetry": self.binder.sanitized_telemetry(),
        }

    def select_optimal_squad(self, task_prompt: str, max_agents: int = 6) -> dict[str, Any]:
        """Automatically selects the optimal multi-agent squad, skills & plugins for any task."""
        low = task_prompt.lower()
        tokens = set(re.findall(r"[a-z0-9_-]{3,}", low))

        matched_domains: list[tuple[int, str]] = []
        for dom_name, dom_spec in DOMAIN_TAXONOMY.items():
            hits = sum(1 for kw in dom_spec["keywords"] if kw in low)
            if hits > 0:
                matched_domains.append((hits, dom_name))
        matched_domains.sort(reverse=True)
        active_domains = [d for _, d in matched_domains[:3]] or ["code_ast_ide_correction"]

        scored: list[tuple[float, str]] = []
        preferred_set: list[str] = []
        recommended_skills: list[str] = []
        for d in active_domains:
            for pa in DOMAIN_TAXONOMY[d]["preferred_agents"]:
                if pa not in preferred_set:
                    preferred_set.append(pa)
            for sk in DOMAIN_TAXONOMY[d]["skills"]:
                if sk not in recommended_skills:
                    recommended_skills.append(sk)

        for name, spec in self._agents_cache.items():
            score = 1.0
            if name in preferred_set:
                score += 50.0 - preferred_set.index(name)
            haystack = f"{name} {spec['description']}".lower()
            for tok in tokens:
                if tok in haystack:
                    score += 3.5
            if spec["resolved_provider"] in ("openai", "google"):
                score += 2.0
            if spec["zero_key_local_capable"]:
                score += 1.5
            scored.append((score, name))

        scored.sort(key=lambda x: (-x[0], x[1]))
        chosen_names = [name for _, name in scored[:max_agents]]
        squad_specs = [self._agents_cache[n] for n in chosen_names if n in self._agents_cache]

        return {
            "ok": True,
            "manual_selection_required": False,
            "detected_domains": active_domains,
            "selected_squad_size": len(squad_specs),
            "selected_squad": squad_specs,
            "activated_skills": recommended_skills,
            "execution_profile": {
                "temperature": 1.0,
                "reasoning_effort": "max",
                "context_window": 1048576,
                "max_output_tokens": 65536,
            },
        }

    def build_sdk_subagents(self, task_prompt: str, max_agents: int = 6) -> list[Any]:
        """Builds native `google.antigravity.types.SubagentConfig` objects for the selected squad."""
        from google.antigravity import types

        selection = self.select_optimal_squad(task_prompt, max_agents=max_agents)
        subagents: list[Any] = []
        for spec in selection["selected_squad"]:
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", spec["name"])[:63]
            subagents.append(
                types.SubagentConfig(
                    name=safe_name,
                    description=spec["description"][:240] or f"Specialist {safe_name}",
                    system_instructions=(
                        f"[ANTIGRAVITY OMNI-SQUAD AGENT: {spec['name']}]\n"
                        f"Provider: {spec['resolved_provider']} | Model: {spec['default_model']}\n"
                        f"{spec['instructions_excerpt']}"
                    ),
                    tools=list(ZERO_KEY_LOCAL_TOOLS),
                )
            )
        return subagents

    def dispatch_squad_parallel(self, task_prompt: str, max_agents: int = 4) -> dict[str, Any]:
        """Dispatches the auto-selected squad in parallel across live bound gateways (`Task Running`)."""
        selection = self.select_optimal_squad(task_prompt, max_agents=max_agents)
        squad = selection["selected_squad"]

        def _invoke_member(spec: dict[str, Any]) -> dict[str, Any]:
            t0 = time.perf_counter()
            prov = spec["resolved_provider"]
            _, key = self.binder.next_key(prov)
            meta = PROVIDER_ENDPOINTS.get(prov, PROVIDER_ENDPOINTS["openai"])
            gw_url = meta["gateway_url"]
            model = meta["default_model"]

            target_url = f"{gw_url.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            }
            body: dict[str, Any] = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"Você é {spec['name']} ({spec['description'][:140]}) no Esquadrão Automático Antigravity SDK. "
                            "Responda de forma cirúrgica, objetiva e verificável em pt-BR."
                        ),
                    },
                    {"role": "user", "content": task_prompt[:3000]},
                ],
                "max_tokens": 220,
                "temperature": 1.0,
            }
            try:
                req = urllib.request.Request(
                    target_url,
                    data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=18) as resp:
                    raw = json.loads(resp.read().decode("utf-8", errors="replace"))
                    content = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                    usage = raw.get("usage") or {}
                    return {
                        "agent": spec["name"],
                        "provider": prov,
                        "http_status": resp.status,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                        "tokens": int(usage.get("total_tokens") or max(1, len(content.split()))),
                        "response": redact_dlp(content[:500]),
                    }
            except (OSError, ValueError, urllib.error.URLError, TimeoutError):
                try:
                    _, oa_key = self.binder.next_key("openai")
                    fb_body = dict(body, model="gpt-5.4-mini")
                    fb_req = urllib.request.Request(
                        "http://127.0.0.1:3080/v1/chat/completions",
                        data=json.dumps(fb_body, ensure_ascii=False).encode("utf-8"),
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {oa_key}"},
                        method="POST",
                    )
                    with urllib.request.urlopen(fb_req, timeout=15) as resp2:
                        raw2 = json.loads(resp2.read().decode("utf-8", errors="replace"))
                        content2 = (((raw2.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                        return {
                            "agent": spec["name"],
                            "provider": f"{prov}->openai_3080_failover",
                            "http_status": resp2.status,
                            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                            "tokens": int((raw2.get("usage") or {}).get("total_tokens") or max(1, len(content2.split()))),
                            "response": redact_dlp(content2[:500]),
                        }
                except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc2:
                    local_ans = ZERO_KEY_LOCAL_TOOLS[4](task_prompt[:600])
                    return {
                        "agent": spec["name"],
                        "provider": f"{prov}->llama_metal4_local",
                        "http_status": 200 if local_ans and not local_ans.startswith("[") else 0,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                        "tokens": len(local_ans.split()),
                        "response": redact_dlp(local_ans[:400]) or str(type(exc2).__name__),
                    }

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(squad))) as pool:
            results = list(pool.map(_invoke_member, squad))

        return {
            "ok": all(r["http_status"] == 200 for r in results),
            "detected_domains": selection["detected_domains"],
            "squad_count": len(results),
            "results": results,
        }
