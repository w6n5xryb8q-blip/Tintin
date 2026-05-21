import pytest

from app.verify import DisallowedHostError, fetch, verify_citation


def test_fetch_rejects_disallowed_host():
    with pytest.raises(DisallowedHostError):
        fetch("https://example.com/something")


def test_fetch_rejects_relative_or_empty():
    with pytest.raises(DisallowedHostError):
        fetch("not-a-url")


def test_verify_citation_disallowed_host_short_circuits():
    result = verify_citation("https://evil.test/page", "any quote")
    assert not result.passed
    assert any("disallowed" in n for n in result.notes)
