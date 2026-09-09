#!/usr/bin/env python3
"""Fail when a role's argument_specs defaults drift from defaults/main.yml.

Every role in this collection declares its variables twice: the runtime
values live in ``defaults/main.yml`` and the documented contract lives in
``meta/argument_specs.yml``. Ansible never cross-checks the two, so a
``default:`` in argument_specs can silently go stale (a real example: a role
whose argument_specs said ``latest`` while defaults pinned a version). Stale
argument_specs mislead anyone auditing image pins from the docs alone, so this
script makes the mismatch a CI failure.

For every ``roles/<role>/`` it loads both files and, for each option under
``argument_specs.main.options`` that declares a ``default:``, requires the
YAML-loaded value to equal the one in ``defaults/main.yml``. A key present in
argument_specs but missing from defaults is a failure; options without a
``default:`` are skipped (they are typically ``required: true``).

The script is strictly read-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(2)

MISSING = object()


def load_yaml(path: Path) -> dict:
    """Load a YAML mapping, treating an empty file as an empty mapping."""
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at top level")
    return data


def fmt(value: object) -> str:
    """Render a value unambiguously (quotes strings, so "2.38.4" != 2.38.4)."""
    if value is MISSING:
        return "<missing>"
    return json.dumps(value, sort_keys=True)


def check_role(role_dir: Path) -> tuple[list[str], int]:
    """Return (mismatch lines, number of options with a default) for one role."""
    specs_path = role_dir / "meta" / "argument_specs.yml"
    defaults_path = role_dir / "defaults" / "main.yml"
    role = role_dir.name

    specs = load_yaml(specs_path)
    defaults = load_yaml(defaults_path) if defaults_path.is_file() else {}

    options = specs.get("argument_specs", {}).get("main", {}).get("options", {}) or {}

    mismatches: list[str] = []
    checked = 0
    for name, option in options.items():
        if not isinstance(option, dict) or "default" not in option:
            continue
        checked += 1
        spec_default = option["default"]
        actual = defaults.get(name, MISSING)
        if actual is MISSING or actual != spec_default:
            mismatches.append(
                f"{role}/{name}: argument_specs={fmt(spec_default)} defaults={fmt(actual)}"
            )
    return mismatches, checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "collection_root",
        nargs="?",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="collection root containing roles/ (default: the repo this script lives in)",
    )
    args = parser.parse_args()

    roles_dir = args.collection_root / "roles"
    if not roles_dir.is_dir():
        sys.stderr.write(f"error: no roles/ directory under {args.collection_root}\n")
        return 2

    all_mismatches: list[str] = []
    roles_checked = 0
    options_checked = 0
    for role_dir in sorted(p for p in roles_dir.iterdir() if p.is_dir()):
        if not (role_dir / "meta" / "argument_specs.yml").is_file():
            print(f"skip: {role_dir.name} has no meta/argument_specs.yml")
            continue
        try:
            mismatches, checked = check_role(role_dir)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            sys.stderr.write(f"error: {role_dir.name}: {exc}\n")
            return 2
        roles_checked += 1
        options_checked += checked
        all_mismatches.extend(mismatches)

    for line in all_mismatches:
        print(line)

    verdict = "FAIL" if all_mismatches else "OK"
    print(
        f"{verdict}: {roles_checked} roles, {options_checked} options with defaults, "
        f"{len(all_mismatches)} mismatch(es)"
    )
    return 1 if all_mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
