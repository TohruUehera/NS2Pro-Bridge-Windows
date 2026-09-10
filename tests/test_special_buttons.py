from __future__ import annotations

from ns2pro_bridge.special_buttons import KEY_CHORDS, SpecialButtonRouter


def test_keyboard_actions_are_edge_triggered() -> None:
    sent: list[tuple[int, ...]] = []
    router = SpecialButtonRouter(
        {"capture": "key_f12", "c": "key_shift_tab"}, sent.append
    )

    assert router.route({"capture"}) == set()
    assert router.route({"capture"}) == set()
    assert router.route(set()) == set()
    assert router.route({"capture", "c"}) == set()
    assert sent == [KEY_CHORDS["key_f12"], KEY_CHORDS["key_f12"], KEY_CHORDS["key_shift_tab"]]


def test_special_button_can_alias_a_held_xinput_button() -> None:
    router = SpecialButtonRouter(
        {"gl": "xinput_l3", "gr": "xinput_rb"}, lambda _keys: None
    )
    assert router.route({"gl", "gr"}) == {"l3", "r"}
    assert router.route({"gl"}) == {"l3"}


def test_disabled_and_unknown_actions_do_nothing() -> None:
    sent: list[tuple[int, ...]] = []
    router = SpecialButtonRouter(
        {"capture": "disabled", "c": "not-an-action"}, sent.append
    )
    assert router.route({"capture", "c"}) == set()
    assert sent == []
