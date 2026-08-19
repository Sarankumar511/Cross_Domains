from bridgescout.api.formatting import (
    clean_gap_title,
    gap_headline,
    score_status_label,
    short_title,
)


def test_clean_gap_title_strips_however_prefix():
    text = "However, the model's performance drops sharply when applied to new domains."
    assert clean_gap_title(text) == "The model's performance drops sharply when applied to new domains"


def test_clean_gap_title_strips_key_limitation_prefix():
    text = "A key limitation is that it lacks a mechanism to adapt to distribution shift."
    assert clean_gap_title(text) == "It lacks a mechanism to adapt to distribution shift"


def test_clean_gap_title_strips_future_work_prefix():
    text = "Future work should explore lightweight adaptation strategies."
    assert clean_gap_title(text) == "Lightweight adaptation strategies"


def test_clean_gap_title_leaves_plain_sentence_unchanged_besides_capitalization():
    text = "the sensors degrade over time in humid conditions."
    assert clean_gap_title(text) == "The sensors degrade over time in humid conditions"


def test_short_title_truncates_with_ellipsis():
    long_text = "a" * 40
    result = short_title(long_text, max_len=10)
    assert len(result) == 10
    assert result.endswith("...")


def test_short_title_leaves_short_text_unchanged():
    assert short_title("short", max_len=10) == "short"


def test_gap_headline_caps_word_count():
    text = "However, " + " ".join(f"word{i}" for i in range(20))
    headline = gap_headline(text, max_words=5)
    assert headline.endswith("...")
    assert len(headline.split()[:-1]) <= 5


def test_score_status_label_threshold():
    assert score_status_label(0.5) == "Strong match"
    assert score_status_label(0.75) == "Strong match"
    assert score_status_label(0.49) == "Needs review"
    assert score_status_label(0.0) == "Needs review"
