from venus_basestation.theme import DARK, LIGHT, blend, get_theme


def test_blend_endpoints_and_midpoint() -> None:
    assert blend("#000000", "#ffffff", 0.0) == "#000000"
    assert blend("#000000", "#ffffff", 1.0) == "#ffffff"
    assert blend("#000000", "#ffffff", 0.5) == "#808080"


def test_blend_clamps_t() -> None:
    assert blend("#102030", "#405060", -1.0) == "#102030"
    assert blend("#102030", "#405060", 2.0) == "#405060"


def test_get_theme_falls_back_to_dark() -> None:
    assert get_theme("dark") is DARK
    assert get_theme("light") is LIGHT
    assert get_theme("does-not-exist") is DARK
    assert get_theme(None) is DARK


def test_trail_shades_end_with_pure_color() -> None:
    shades = DARK.trail_shades("#38bdf8")
    assert len(shades) == 3
    assert shades[-1] == "#38bdf8"
    assert all(shade.startswith("#") and len(shade) == 7 for shade in shades)


def test_battery_color_thresholds() -> None:
    assert DARK.battery_color(90) == DARK.ok
    assert DARK.battery_color(45) == DARK.warn
    assert DARK.battery_color(10) == DARK.danger
    assert DARK.battery_color(None) == DARK.text_faint


def test_object_style_has_fallback() -> None:
    color, shape = DARK.object_style("not-a-real-event")
    assert shape == "oval"
    assert color == DARK.text_muted
