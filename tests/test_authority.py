from app import authority


def test_attach_authority_resolves_pub_463():
    chain = authority.attach_authority("Pub 463")
    assert "162" in chain.irc
    assert any("Flowers" in c.cite for c in chain.cases)


def test_attach_authority_normalizes_pub_string():
    a = authority.attach_authority("Publication 587")
    b = authority.attach_authority("587")
    assert a.irc == b.irc
    assert "280A" in a.irc


def test_format_authority_block_lists_all_tiers():
    chain = authority.attach_authority("Pub 463")
    block = authority.format_authority_block(chain)
    assert "IRC §162" in block
    assert "Treas. Reg." in block
    assert "Flowers" in block


def test_format_authority_block_empty():
    chain = authority.AuthorityChain(pub_number="9999")
    block = authority.format_authority_block(chain)
    assert "none mapped" in block


def test_verify_authority_currency_flags_amendment_after_pub():
    chain = authority.attach_authority("Pub 590B")  # cites IRC 408
    warnings = authority.verify_authority_currency(
        chain,
        pub_revision_date="2020-01-01",
        effective_dates={"IRC 408": "2022-12-29"},  # SECURE 2.0
    )
    assert warnings
    assert warnings[0].kind == "irc_amended"
    assert "408" in warnings[0].detail


def test_new_pubs_have_authority_chains():
    # The PDFs we ingested must each resolve to a non-empty xref entry,
    # otherwise the authority block in the answer will be "(none mapped)".
    for pub in ["334", "501", "502", "505", "525", "463", "936"]:
        chain = authority.attach_authority(pub)
        assert not chain.is_empty, f"missing xref for Pub {pub}"


def test_pub_936_carries_tcja_note():
    # The cap-on-acquisition-debt fact is a frequent staff-level error;
    # the xref entry's note is the breadcrumb for the escalation brief.
    chain = authority.attach_authority("936")
    assert "163" in chain.irc


def test_verify_authority_currency_clean_when_pub_is_newer():
    chain = authority.attach_authority("Pub 590B")
    warnings = authority.verify_authority_currency(
        chain,
        pub_revision_date="2024-01-01",
        effective_dates={"IRC 408": "2022-12-29"},
    )
    assert warnings == []
