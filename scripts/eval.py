"""Run the golden-question set against the local retriever + authority layer.

This checks Part 6 verification items #5 (citation grounding) and #11 (authority
cross-reference). It does NOT call the LLM — it measures whether the retrieval
and xref layers point at the right Pub and the right IRC/Reg/case mapping.

Usage:
    python scripts/eval.py tests/golden/questions.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from app import authority, retriever


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    items = yaml.safe_load(Path(argv[1]).read_text()) or []

    pub_hits = auth_hits = 0
    total = len(items)
    for it in items:
        q = it["question"]
        gold_pub = str(it["gold_pub"])
        gold_irc = set(map(str, it.get("gold_irc", [])))

        chunks = retriever.query(q, k=4)
        top_pubs = [c.pub_number for c in chunks]
        if gold_pub in top_pubs[:2]:
            pub_hits += 1
        if top_pubs:
            chain = authority.attach_authority(top_pubs[0])
            if gold_irc and gold_irc.intersection(set(chain.irc)):
                auth_hits += 1

    print(f"pub@2 accuracy:        {pub_hits}/{total} = {pub_hits / total:.0%}")
    print(f"authority match rate:  {auth_hits}/{total} = {auth_hits / total:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
