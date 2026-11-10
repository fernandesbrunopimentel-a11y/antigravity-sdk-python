# Copyright 2026 Fisioimagem / Antigravity Sovereign Omni-Fleet Extension
"""Unified Antigravity SDK Omni-Fleet Package (`google.antigravity.omni_fleet`)."""

from __future__ import annotations

from typing import Any

from google.antigravity.omni_fleet.ide_code_healer import (
    BackgroundIdeCodeHealer,
    load_immutable_protected_paths,
)
from google.antigravity.omni_fleet.squad_orchestrator import (
    DOMAIN_TAXONOMY,
    OmniSquadOrchestrator,
)
from google.antigravity.omni_fleet.vault_key_binder import (
    PRIORITY_ORDER,
    PROVIDER_ENDPOINTS,
    ZERO_KEY_LOCAL_TOOLS,
    VaultProviderKeyBinder,
    ast_syntax_check,
    dlp_secret_scan,
    fleet_zero_token_health,
    local_ollama_metal_infer,
    pyrefly_type_check,
    redact_dlp,
    ruff_lint_check,
)

__all__ = [
    "DOMAIN_TAXONOMY",
    "PRIORITY_ORDER",
    "PROVIDER_ENDPOINTS",
    "ZERO_KEY_LOCAL_TOOLS",
    "BackgroundIdeCodeHealer",
    "OmniSquadOrchestrator",
    "VaultProviderKeyBinder",
    "ast_syntax_check",
    "create_omni_auto_agent_config",
    "dlp_secret_scan",
    "fleet_zero_token_health",
    "load_immutable_protected_paths",
    "local_ollama_metal_infer",
    "pyrefly_type_check",
    "redact_dlp",
    "ruff_lint_check",
    "select_optimal_squad",
]

_DEFAULT_ORCHESTRATOR: OmniSquadOrchestrator | None = None


def _get_orchestrator() -> OmniSquadOrchestrator:
    global _DEFAULT_ORCHESTRATOR
    if _DEFAULT_ORCHESTRATOR is None:
        _DEFAULT_ORCHESTRATOR = OmniSquadOrchestrator()
    return _DEFAULT_ORCHESTRATOR


def select_optimal_squad(task_prompt: str, max_agents: int = 6) -> dict[str, Any]:
    """Convenience entry point to auto-select the best squad without manual user selection."""
    return _get_orchestrator().select_optimal_squad(task_prompt, max_agents=max_agents)


def create_omni_auto_agent_config(
    task_prompt: str,
    preferred_provider: str | None = None,
    max_subagents: int = 6,
) -> Any:
    """Builds a complete `google.antigravity` AgentConfig pre-loaded with the optimal squad, tools, skills & vault keys."""
    orch = _get_orchestrator()
    subagents = orch.build_sdk_subagents(task_prompt, max_agents=max_subagents)
    selection = orch.select_optimal_squad(task_prompt, max_agents=max_subagents)
    sys_inst = (
        "Você é o Maestro Soberano Antigravity SDK (Auto-Squad Always-Active).\n"
        f"Domínios detectados: {', '.join(selection['detected_domains'])}.\n"
        f"Esquadrão ativo: {', '.join(s['name'] for s in selection['selected_squad'])}.\n"
        f"Skills recomendadas: {', '.join(selection['activated_skills'])}.\n"
        "Use pensamento máximo (effort=max, temp=1.0), zero alucinação e zero vazamento DLP."
    )
    return orch.binder.build_antigravity_sdk_config(
        agent_name="agy-omni-auto-squad-master",
        system_instructions=sys_inst,
        preferred_provider=preferred_provider,
        subagents=subagents,
    )
