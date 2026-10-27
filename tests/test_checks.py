from evaluate import detect_language, keywords_found


def test_detects_arabic():
    assert detect_language("عايز ألغي الاشتراك") == "ar"


def test_detects_english():
    assert detect_language("How do I cancel?") == "en"


def test_mixed_message_uses_majority_script():
    assert detect_language("عايز ألغي الاشتراك بتاعي please") == "ar"


def test_empty_answer_is_unknown():
    assert detect_language("") == "unknown"


def test_keywords_any_match():
    assert keywords_found("You can cancel from Settings", "cancel|Settings")
    assert not keywords_found("Hello!", "cancel|Settings")


def test_no_expected_keywords_passes():
    assert keywords_found("anything", "")
