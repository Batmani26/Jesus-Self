"""Dynamic plugin loader.

Every module in `selfbot/plugins/` that exposes `register(client)` will be loaded.
"""
import importlib
import logging
import pkgutil
from pathlib import Path

log = logging.getLogger("selfbot.loader")

PLUGIN_PKG = "selfbot.plugins"


def load_plugins(client) -> list[str]:
    loaded: list[str] = []
    pkg = importlib.import_module(PLUGIN_PKG)
    pkg_path = Path(pkg.__file__).parent

    # Import all plugin modules in parallel for faster startup
    names = [m.name for m in pkgutil.iter_modules([str(pkg_path)]) if not m.name.startswith("_")]
    full_names = [f"{PLUGIN_PKG}.{n}" for n in names]
    import concurrent.futures as _cf
    with _cf.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(importlib.import_module, full_names))
    # Register sequentially (Telethon event registration is fast)
    for name in names:
        full_name = f"{PLUGIN_PKG}.{name}"
        try:
            module = importlib.import_module(full_name)
            if hasattr(module, "register"):
                module.register(client)
                loaded.append(name)
                log.info("Plugin loaded: %s", name)
            else:
                log.warning("Plugin %s has no register(client)", name)
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to load plugin %s: %s", name, exc)

    return loaded
