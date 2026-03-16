"""Initialize hook registry with all extensions.

Import this module from app.py or any entry point to register
knowledge-inject (P2.7) and P2.5 context monitors into the hook system.

Usage:
    import runtime.init_hooks  # registers knowledge-inject + P2.5 monitors

This module exists as a clean integration bridge to avoid modifying
the 900-line hooks.py via API. It patches HOOK_REGISTRY and
ALWAYS_ON_HOOKS at import time.

After import:
    - HOOK_REGISTRY gains "knowledge-inject" (21 hooks total)
    - ALWAYS_ON_HOOKS gains "knowledge-inject" (3 always-on: reality-check, energy-route, knowledge-inject)
    - get_context_monitors() available for orchestrator use
"""

from runtime.hooks import HOOK_REGISTRY, ALWAYS_ON_HOOKS
from runtime.hooks_scholar import patch_hook_registry, get_context_monitors

patch_hook_registry(HOOK_REGISTRY, ALWAYS_ON_HOOKS)

# Re-export for convenience
__all__ = ["HOOK_REGISTRY", "ALWAYS_ON_HOOKS", "get_context_monitors"]
