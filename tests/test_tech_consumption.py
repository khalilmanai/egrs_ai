from estimators.tech_consumption import estimate_site_kwh, estimate_from_tech_flags, estimate_from_config


def test_estimate_site_kwh_no_tech():
    result = estimate_site_kwh()
    expected = 200.0 * 1.20
    assert result == expected


def test_estimate_site_kwh_4g_only():
    result = estimate_site_kwh(has_4g_fdd=True)
    expected = (200.0 + 600.0) * 1.20
    assert result == expected


def test_estimate_site_kwh_full_tech():
    result = estimate_site_kwh(has_2g=True, has_3g=True, has_4g_fdd=True, has_4g_tdd=True, has_5g=True)
    expected = (200.0 + 250.0 + 250.0 + 600.0 + 400.0 + 1200.0) * 1.20
    assert result == expected


def test_estimate_from_tech_flags():
    flags = {"has_2g": True, "has_3g": False, "has_4g_fdd": True, "has_4g_tdd": False, "has_5g": False}
    result = estimate_from_tech_flags(flags)
    expected = (200.0 + 250.0 + 600.0) * 1.20
    assert result == expected


def test_estimate_from_config():
    result = estimate_from_config("SITE NODAL 4GFDD 2G")
    expected = (200.0 + 250.0 + 600.0) * 1.20
    assert result == expected


def test_estimate_from_config_none():
    result = estimate_from_config(None)
    assert result == 200.0 * 1.20


def test_estimate_from_config_empty():
    result = estimate_from_config("")
    assert result == 200.0 * 1.20
