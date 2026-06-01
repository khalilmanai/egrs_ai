BASE_KWH_MONTH = 200
TECH_KWH = {
    "2g": 250,
    "3g": 250,
    "4g_fdd": 600,
    "4g_tdd": 400,
    "5g": 1200,
}
CLIMATE_FACTOR_TUNISIA = 1.20


def estimate_site_kwh(has_2g: bool = False, has_3g: bool = False,
                      has_4g_fdd: bool = False, has_4g_tdd: bool = False,
                      has_5g: bool = False) -> float:
    total = BASE_KWH_MONTH
    if has_2g:
        total += TECH_KWH["2g"]
    if has_3g:
        total += TECH_KWH["3g"]
    if has_4g_fdd:
        total += TECH_KWH["4g_fdd"]
    if has_4g_tdd:
        total += TECH_KWH["4g_tdd"]
    if has_5g:
        total += TECH_KWH["5g"]
    return round(total * CLIMATE_FACTOR_TUNISIA, 2)


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
