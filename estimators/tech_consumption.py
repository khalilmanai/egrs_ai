from config.settings import get_settings

_settings = get_settings()


def estimate_site_kwh(has_2g: bool = False, has_3g: bool = False,
                      has_4g_fdd: bool = False, has_4g_tdd: bool = False,
                      has_5g: bool = False) -> float:
    total = _settings.tech_base_kwh_month
    if has_2g:
        total += _settings.tech_2g_kwh
    if has_3g:
        total += _settings.tech_3g_kwh
    if has_4g_fdd:
        total += _settings.tech_4g_fdd_kwh
    if has_4g_tdd:
        total += _settings.tech_4g_tdd_kwh
    if has_5g:
        total += _settings.tech_5g_kwh
    return round(total * _settings.tech_climate_factor, 2)


def estimate_from_config(config: str | None) -> float:
    if not config:
        return estimate_site_kwh()
    config_lower = config.lower()
    return estimate_site_kwh(
        has_2g="2g" in config_lower,
        has_3g="3g" in config_lower,
        has_4g_fdd="4g fdd" in config_lower or "4gfdd" in config_lower,
        has_4g_tdd="4g tdd" in config_lower or "4gtdd" in config_lower,
        has_5g="5g" in config_lower,
    )


def estimate_from_tech_flags(flags: dict) -> float:
    return estimate_site_kwh(
        has_2g=flags.get("has_2g", False),
        has_3g=flags.get("has_3g", False),
        has_4g_fdd=flags.get("has_4g_fdd", False),
        has_4g_tdd=flags.get("has_4g_tdd", False),
        has_5g=flags.get("has_5g", False),
    )
