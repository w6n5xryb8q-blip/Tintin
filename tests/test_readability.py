from app.readability import score


def test_simple_text_passes():
    text = "You can deduct the cost. The IRS allows it. Keep your receipts."
    assert score(text).passed


def test_complex_text_fails():
    text = (
        "Notwithstanding the foregoing, the taxpayer's entitlement to the deduction is "
        "predicated upon contemporaneous substantiation in conformity with §274(d) "
        "promulgations and corresponding Treasury Regulation interpretive guidance."
    )
    assert not score(text).passed
