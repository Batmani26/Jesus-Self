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

    for mod_info in pkgutil.iter_modules([str(pkg_path)]):
        if mod_info.name.startswith("_"):
            continue
        full_name = f"{PLUGIN_PKG}.{mod_info.name}"
        try:
            module = importlib.import_module(full_name)
            if hasattr(module, "register"):
                module.register(client)
                loaded.append(mod_info.name)
                log.info("Plugin loaded: %s", mod_info.name)
            else:
                log.warning("Plugin %s has no register(client)", mod_info.name)
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to load plugin %s: %s", mod_info.name, exc)

    return loaded
