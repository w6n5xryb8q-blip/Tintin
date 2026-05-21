from app.confidence import Bucket, ConfidenceSignals, bucket_for


def _sig(**over):
    base = dict(
        retrieval_score=0.9,
        quote_grounded=True,
        self_consistency=0.9,
        currency_ok=True,
        hard_escalate=False,
        authority_concordance_ok=True,
    )
    base.update(over)
    return ConfidenceSignals(**base)


def test_solid_when_all_signals_strong():
    b, _ = bucket_for(_sig())
    assert b is Bucket.SOLID


def test_hard_escalate_overrides_everything():
    b, _ = bucket_for(_sig(hard_escalate=True))
    assert b is Bucket.ESCALATE


def test_authority_concordance_downgrades():
    b, reason = bucket_for(_sig(authority_concordance_ok=False))
    assert b is Bucket.USE_WITH_CAUTION
    assert "authority" in reason.lower()


def test_stale_pub_downgrades():
    b, _ = bucket_for(_sig(currency_ok=False))
    assert b is Bucket.USE_WITH_CAUTION


def test_quote_not_grounded_downgrades():
    b, _ = bucket_for(_sig(quote_grounded=False))
    assert b is Bucket.USE_WITH_CAUTION


def test_moderate_signals_yield_mostly_solid():
    b, _ = bucket_for(_sig(retrieval_score=0.65, self_consistency=0.65))
    assert b is Bucket.MOSTLY_SOLID


def test_weak_signals_yield_use_with_caution():
    b, _ = bucket_for(_sig(retrieval_score=0.3, self_consistency=0.4))
    assert b is Bucket.USE_WITH_CAUTION
