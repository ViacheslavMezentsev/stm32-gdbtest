"""
RU: Настройки прогона и источники конфигурации только для чтения.
EN: Read-only run settings and configuration sources.
"""
from stm32_gdbtest import case


# Both views are frozen: reading works, mutation raises.
@case("HW_CI_SETTINGS", timeout_s=45, labels=("api", "settings"), contracts=("ci_app_api",))
def settings_views(target):
    # settings is the effective configuration and equals the 0.2.x name.
    target.check("settings matches config", target.settings is target.config, True)
    target.check("settings expose the api schema", target.settings["api"]["schema"], 1)
    target.check("settings expose the records limits",
                 target.settings["api"]["records"]["max_records"] > 0, True)
    target.check("settings expose the execute limit",
                 target.settings["api"]["execute"]["output_limit_chars"] > 0, True)
    target.check("settings expose the reset command",
                 target.settings["api"]["reset"]["command"] in ("monitor reset", "monitor reset halt"),
                 True)

    # A read-only mapping refuses mutation instead of silently accepting it.
    try:
        target.settings["api"] = {}
    except TypeError:
        target.check("settings refuse assignment", True, True)
    else:
        target.check("settings refuse assignment", False, True)
    try:
        target.settings["api"]["records"]["max_records"] = 1
    except TypeError:
        target.check("nested settings refuse assignment", True, True)
    else:
        target.check("nested settings refuse assignment", False, True)

    # sources describes where the configuration came from.
    target.check("sources match config_props", target.sources is target.config_props, True)
    target.check("sources name the api reference", target.sources["api"]["reference"], "api.toml")
    target.check("sources carry a digest", len(target.sources["api"]["sha256"]), 64)
    target.check("sources expose the captured data",
                 target.sources["api"]["data"]["schema"], 1)
    try:
        target.sources["api"]["reference"] = "other.toml"
    except TypeError:
        target.check("sources refuse assignment", True, True)
    else:
        target.check("sources refuse assignment", False, True)

    # The 0.2.x names still return the same frozen objects.
    target.check("config matches settings", target.config is target.settings, True)
    target.check("config_props match sources", target.config_props is target.sources, True)
