#!/usr/bin/env python3
"""Run every V3 unittest exactly once across deterministic CI shards.

Equivalent to: python -m unittest discover -s tests -p "v3_*test.py"
Each process independently discovers the same complete inventory, then selects
its disjoint subset by sorted test ID. Failures remain hard CI failures.
"""
import argparse
import hashlib
from pathlib import Path
import sys
import unittest


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.count <= 16 or not 0 <= args.index < args.count:
        parser.error("expected 1 <= count <= 16 and 0 <= index < count")

    tests_dir = Path(__file__).resolve().parent
    suite = unittest.TestLoader().discover(
        start_dir=str(tests_dir), pattern="v3_*test.py",
        top_level_dir=str(tests_dir))
    inventory = sorted(cases(suite), key=lambda case: case.id())
    ids = [case.id() for case in inventory]
    if not inventory or len(ids) != len(set(ids)):
        raise RuntimeError("empty or duplicate V3 test inventory")
    # A stable inventory digest makes each shard's complete coverage auditable.
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    selected = [case for index, case in enumerate(inventory)
                if index % args.count == args.index]
    if not selected:
        raise RuntimeError("empty V3 test shard")
    print(f"V3 suite: {len(ids)} unique tests; inventory sha256={digest}", flush=True)
    print(f"Shard {args.index + 1}/{args.count}: {len(selected)} tests", flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
