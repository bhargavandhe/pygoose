from __future__ import annotations

import asyncio
from typing import Any, Callable

# Hook type constants
PRE_VALIDATE = "pre_validate"
PRE_SAVE = "pre_save"
POST_SAVE = "post_save"
PRE_DELETE = "pre_delete"
POST_DELETE = "post_delete"
POST_UPDATE = "post_update"

_ALL_HOOKS = (PRE_VALIDATE, PRE_SAVE, POST_SAVE, PRE_DELETE, POST_DELETE, POST_UPDATE)


def _make_hook_decorator(hook_type: str) -> Callable:
    """Create a decorator that stamps _pygoose_hook on the method."""

    def decorator(fn: Callable) -> Callable:
        if not hasattr(fn, "_pygoose_hooks"):
            fn._pygoose_hooks = []
        fn._pygoose_hooks.append(hook_type)
        return fn

    return decorator


pre_validate = _make_hook_decorator(PRE_VALIDATE)
pre_save = _make_hook_decorator(PRE_SAVE)
post_save = _make_hook_decorator(POST_SAVE)
pre_delete = _make_hook_decorator(PRE_DELETE)
post_delete = _make_hook_decorator(POST_DELETE)
post_update = _make_hook_decorator(POST_UPDATE)


def collect_hooks(cls: type) -> dict[str, list[str]]:
    """Walk MRO in reverse and collect methods decorated with hook decorators.

    Returns a dict mapping hook_type -> list of method names, in MRO order
    (parent hooks first).
    """
    hooks: dict[str, list[str]] = {h: [] for h in _ALL_HOOKS}
    seen: dict[str, set[str]] = {h: set() for h in _ALL_HOOKS}

    # Reverse MRO so parent hooks come first
    for klass in reversed(cls.__mro__):
        for name, method in vars(klass).items():
            hook_types = getattr(method, "_pygoose_hooks", None)
            if hook_types:
                for ht in hook_types:
                    if name not in seen[ht]:
                        hooks[ht].append(name)
                        seen[ht].add(name)

    return hooks


async def run_hooks(instance: Any, hook_type: str) -> None:
    """Run all hooks of the given type on a document instance."""
    hook_methods = instance.__class__._hooks.get(hook_type, [])
    for method_name in hook_methods:
        method = getattr(instance, method_name)
        result = method()
        if asyncio.iscoroutine(result):
            await result
