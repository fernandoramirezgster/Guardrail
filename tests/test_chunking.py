"""División en ventanas: un prompt largo no se trunca antes de clasificarse."""
import pytest

from app.classifiers.hf_classifier import split_into_windows


def test_short_text_is_single_window():
    assert split_into_windows([1, 2, 3], window=5, stride=1) == [[1, 2, 3]]


def test_windows_cover_every_token_with_overlap():
    tokens = list(range(1000))
    windows = split_into_windows(tokens, window=510, stride=64)
    assert windows[0][0] == 0
    assert windows[-1][-1] == 999
    assert all(len(w) <= 510 for w in windows)
    assert set(tokens) == {t for w in windows for t in w}
    # Ventanas consecutivas comparten `stride` tokens.
    assert windows[0][-64:] == windows[1][:64]


def test_injection_at_the_end_lands_in_last_window():
    tokens = ["benigno"] * 2000 + ["INYECCION"]
    windows = split_into_windows(tokens, window=510, stride=64)
    assert "INYECCION" in windows[-1]


@pytest.mark.parametrize("window,stride", [(0, 0), (10, 10), (10, -1)])
def test_invalid_window_parameters(window, stride):
    with pytest.raises(ValueError):
        split_into_windows([1, 2, 3], window=window, stride=stride)
