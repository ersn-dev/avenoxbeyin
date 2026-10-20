#!/usr/bin/env python3
"""Evaluate staged retrieval on a synthetic vault; no model calls or vault writes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

import evaluate_v3_passages as base


def opened(vault, record, sentence):
    """Score a source only after retrieval has passed the memory access gates."""
    source, expected = record.get("source"), record.get("source_sha256")
    if not isinstance(source, str) or not isinstance(expected, str):
        return False
    try:
        root = vault.resolve()
        path = root.joinpath(source)
        # Do not allow symlinks or paths escaping the synthetic vault.
        if not path.resolve(strict=True).is_relative_to(root):
            return False
        relative = path.relative_to(root)
        cursor = root
        for component in relative.parts:
            cursor = cursor / component
            if cursor.is_symlink():
                return False
        data = path.read_bytes()
        return (hashlib.sha256(data).hexdigest() == expected and
                base._normal(sentence) in base._normal(data.decode("utf-8")))
    except (ValueError, OSError, UnicodeError):
        return False


def strict_candidates(store, query):
    # Preserve strict note-level eligibility; exclude categories ignored by
    # automatic passage injection. Candidates are not auto-injected.
    records = store.retrieve(query, strict=True, limit=5, budget_chars=8000)["records"]
    prefixes = tuple(p.casefold() for p in base.passage.settings(store.state_dir)["exclude"])
    return [r for r in records
            if not r["source"].casefold().startswith(prefixes)]


def measure(store, root, labelled, budget):
    results = {}
    for shape in ("short", "long"):
        counts = {"count": 0, "initial_answer": 0, "source_recall": 0,
                  "opened_source_answer": 0, "stage2_potential_answer": 0,
                  "abstention_recovered": 0}
        for item in labelled["questions"]:
            query = item["query"]
            if shape == "long":
                query = base.LONG_PREFIX + query + "?" + base.LONG_SUFFIX
            first = base._deliver(store, query, budget)["records"]
            target = next((r for r in first if r["source"] == item["source"]), None)
            initial = bool(target and base._normal(item["sentence"]) in base._normal(target["text"]))
            open_first = bool(target and opened(root, target, item["sentence"]))
            second = strict_candidates(store, query)
            recovered = any(r["source"] == item["source"] and
                            opened(root, r, item["sentence"]) for r in second)
            counts["count"] += 1
            counts["initial_answer"] += int(initial)
            counts["source_recall"] += int(target is not None)
            counts["opened_source_answer"] += int(open_first)
            counts["stage2_potential_answer"] += int(initial or open_first or recovered)
            counts["abstention_recovered"] += int(not first and recovered)
        n = counts["count"]
        results[shape] = {**counts, "rates": {
            k: round(v / n, 4) for k, v in counts.items() if k != "count"
        }}
    controls = {}
    for group, prompts in labelled["controls"].items():
        injected = false_leads = 0
        for prompt in prompts:
            initial = base._deliver(store, prompt, budget)["records"]
            injected += int(bool(initial))
            if not initial:
                false_leads += int(bool(strict_candidates(store, prompt)))
        controls[group] = {"queries": len(prompts), "initial_noise": injected,
                           "stage2_false_leads_after_abstention": false_leads}
    return {"questions": results, "controls": controls}


def cross_block_diagnostic():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "vault"
        root.mkdir()
        store = base.runtime.MemoryStore(Path(tmp) / "state", root)
        filler = " ".join(f"dolgu{i} kelime{i % 7} satir{i % 11}." for i in range(60))
        text = "Zirkon notu burada durur. " + filler + "\n\n" + filler + " Kobalt ise başka paragrafta."
        source = "knowledge/split.md"
        path = root / source
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
        store.ingest({"id": "split", "kind": "note", "visibility": "internal",
                      "source": source, "text": text, "facts": {},
                      "updated_at": "2026-09-20T10:00:00Z"})
        first = base._deliver(store, "zirkon kobalt", 5000)["records"]
        second = strict_candidates(store, "zirkon kobalt")
        return {"initial_sources": [r["source"] for r in first],
                "second_sources": [r["source"] for r in second],
                "recovered": (not first and any(
                    r["source"] == source and opened(root, r, "Zirkon notu burada durur.")
                    for r in second))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", type=int, default=83)
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix="v3-staged-evidence-") as tmp:
        root = Path(tmp) / "vault"
        root.mkdir()
        notes, labelled = base.synthetic_corpus(args.seed)
        store = base.runtime.MemoryStore(Path(tmp) / "state", root)
        base._ingest_notes(store, root, notes)
        store.STRICT_PASSAGES = True
        eligible, _ = store._eligible()
        base.passage.build(store.state_dir, base.passage.pool(store, eligible))
        report = {
            "source_version": (Path(__file__).resolve().parents[1] / "VERSION").read_text().strip(),
            "scope": "synthetic; read-only evaluator; no automatic second-stage routing",
            "seed": args.seed, "questions": len(labelled["questions"]),
            "diagnostic": cross_block_diagnostic(),
            "budgets": {str(b): measure(store, root, labelled, b) for b in (2000, 5000)}
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    d = report["diagnostic"]
    print(f"Source v{report['source_version']}; cross-block recovered: {d['recovered']}")
    for budget, values in report["budgets"].items():
        for shape, row in values["questions"].items():
            n = row["count"]
            print(f"{budget} {shape}: initial={row['initial_answer']}/{n}, "
                  f"open={row['opened_source_answer']}/{n}, "
                  f"stage2 upper bound={row['stage2_potential_answer']}/{n}")
    if not d["recovered"]:
        raise SystemExit("Known cross-block source was not recovered")


if __name__ == "__main__":
    main()
