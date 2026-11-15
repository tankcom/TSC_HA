#!/usr/bin/env python3
"""Offline consistency checks for the TeslaSolarCharger integration.

Run from the repository root:  python scripts/check_integration.py

No Home Assistant installation is required - the integration is parsed with the
standard library only.  The script verifies that

* every python file is syntactically valid,
* every json file (manifest, strings, translations, hacs.json) is valid,
* every translation key used by the code exists in strings.json and in each
  translation file,
* strings.json does not contain unused entity keys.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "tesla_solar_charger"

SPEC_TO_PLATFORM = {"SensorSpec": "sensor", "BinarySensorSpec": "binary_sensor"}
KIND_TO_PLATFORM = {
    "number": "number",
    "bool": "switch",
    "text": "text",
    "secret": "text",
    "select": "select",
}
DESCRIPTION_FUNCS = {"select_description": "select", "button_description": "button"}


def python_files() -> list[Path]:
    return sorted(COMPONENT.rglob("*.py"))


def json_files() -> list[Path]:
    translation_dir = COMPONENT / "translations"
    return sorted(
        [COMPONENT / "manifest.json", COMPONENT / "strings.json", ROOT / "hacs.json",
         *translation_dir.glob("*.json")]
    )


def collect_keys(files: list[Path]) -> dict[str, set[str]]:
    """Return the translation keys used per platform."""
    found: dict[str, set[str]] = {}
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name is None or not node.args:
                continue
            first = node.args[0]
            if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
                continue
            if name in SPEC_TO_PLATFORM:
                found.setdefault(SPEC_TO_PLATFORM[name], set()).add(first.value)
            elif name == "FieldSpec":
                kind = None
                if len(node.args) >= 3 and isinstance(node.args[2], ast.Constant):
                    kind = node.args[2].value
                else:
                    for kw in node.keywords:
                        if kw.arg == "kind" and isinstance(kw.value, ast.Constant):
                            kind = kw.value.value
                platform = KIND_TO_PLATFORM.get(str(kind))
                if platform and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    found.setdefault(platform, set()).add(str(node.args[1].value))
            elif name in DESCRIPTION_FUNCS:
                found.setdefault(DESCRIPTION_FUNCS[name], set()).add(first.value)


def main(argv: list[str] | None = None) -> int:
    """Run the checks and print the keys the code uses."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-keys",
        action="store_true",
        help="only print the translation keys used by the integration",
    )
    args = parser.parse_args(argv)

    files = python_files()
    keys = collect_keys(files)
    if args.print_keys:
        for platform in sorted(keys):
            print(f"[{platform}]")
            for key in sorted(keys[platform]):
                print(f"  {key}")
        return 0

    problems: list[str] = []
    for path in files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as err:  # pragma: no cover - reported below
            problems.append(f"{path.relative_to(ROOT)}: syntax error: {err}")

    parsed: dict[Path, dict] = {}
    for path in json_files():
        if not path.exists():
            problems.append(f"missing file: {path.relative_to(ROOT)}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            problems.append(f"{path.relative_to(ROOT)}: invalid json: {err}")
            continue
        parsed[path] = data

    manifest = parsed.get(COMPONENT / "manifest.json", {})
    if manifest.get("domain") != COMPONENT.name:
        problems.append(
            f"manifest domain '{manifest.get('domain')}' != folder '{COMPONENT.name}'"
        )
    for field in (
        "domain",
        "name",
        "codeowners",
        "documentation",
        "issue_tracker",
        "config_flow",
        "integration_type",
        "iot_class",
        "version",
    ):
        if field not in manifest:
            problems.append(f"manifest.json is missing '{field}'")
    if not manifest.get("config_flow"):
        problems.append("manifest.json must set config_flow to true")

    strings = parsed.get(COMPONENT / "strings.json", {})
    entity_strings = strings.get("entity", {})
    for platform in sorted(keys):
        used = keys[platform]
        defined = set(entity_strings.get(platform, {}))
        missing = sorted(used - defined)
        unused = sorted(defined - used)
        if missing:
            problems.append(
                f"strings.json: entity.{platform} missing {len(missing)} key(s): "
                f"{', '.join(missing)}"
            )
        if unused:
            problems.append(
                f"strings.json: entity.{platform} unused key(s): {', '.join(unused)}"
            )

    translation_dir = COMPONENT / "translations"
    for path, data in parsed.items():
        if path.parent != translation_dir:
            continue
        entity_data = data.get("entity", {})
        for platform in sorted(keys):
            missing = sorted(keys[platform] - set(entity_data.get(platform, {})))
            if missing:
                problems.append(
                    f"{path.relative_to(ROOT)}: entity.{platform} missing: "
                    f"{', '.join(missing)}"
                )
        for platform, entries in entity_data.items():
            for key, value in entries.items():
                if isinstance(value, dict) and "name" not in value:
                    problems.append(
                        f"{path.relative_to(ROOT)}: entity.{platform}.{key} has no name"
                    )

    total = sum(len(values) for values in keys.values())
    print(f"translation keys used: {total}")
    for platform in sorted(keys):
        print(f"  {platform}: {len(keys[platform])}")

    if problems:
        print("\nPROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

    return found
