#!/usr/bin/env python3
"""
check-skills -- validate every skill directory under skills/.

A skill is a directory with a SKILL.md whose YAML-ish front matter carries:

    ---
    name: <same as the directory>
    description: <one line, non-empty>
    ---

Rules checked:
  1. SKILL.md exists,
  2. the "---" front matter block exists and carries name + description,
  3. name equals the directory name (case-sensitive),
  4. description is non-empty,
  5. SKILL.md is UTF-8 without a BOM.

Usage:
    tools/check-skills.py                 # every directory under skills/
    tools/check-skills.py skills/foo      # just that one

Exit status is non-zero if anything is wrong, so CI can gate on it.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONT_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.S)


def read_front_matter(path: pathlib.Path) -> dict | None:
    """Parse the small front matter block of a SKILL.md (no YAML dependency)."""
    raw = path.read_bytes()
    if raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError('SKILL.md has a UTF-8 BOM')
    text = raw.decode('utf-8')
    m = FRONT_RE.match(text)
    if not m:
        return None
    fields = {}
    for line in m.group(1).split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition(':')
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '\'"':
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def check_skill(path: pathlib.Path) -> list:
    """Problems with one skill directory; an empty list means it is valid."""
    skill_md = path / 'SKILL.md'
    if not skill_md.is_file():
        return ['%s: missing SKILL.md' % path.name]
    try:
        fields = read_front_matter(skill_md)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return ['%s: %s' % (path.name, exc)]
    if fields is None:
        return ['%s: SKILL.md has no "---" front matter block' % path.name]

    errs = []
    name = fields.get('name', '')
    desc = fields.get('description', '')
    if not name:
        errs.append('%s: front matter has no "name"' % path.name)
    elif name != path.name:
        errs.append('%s: name "%s" does not match the directory' % (path.name, name))
    if not desc:
        errs.append('%s: front matter has no "description"' % path.name)
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description='validate Codex skill directories')
    ap.add_argument('paths', nargs='*', help='skill directories (default: skills/*)')
    ap.add_argument('--root', default=str(ROOT),
                    help='repository root whose skills/ is scanned (default: this checkout)')
    args = ap.parse_args()

    if args.paths:
        roots = [pathlib.Path(p) for p in args.paths]
    else:
        roots = sorted(p for p in (pathlib.Path(args.root) / 'skills').glob('*') if p.is_dir())
    if not roots:
        print('check-skills: no skill directories under skills/ yet')
        return 0

    bad = 0
    for path in roots:
        errs = check_skill(path)
        if errs:
            bad += 1
            print('ERROR %s' % path.name)
            for e in errs:
                print('        - %s' % e)
        else:
            print('ok    %s' % path.name)
    print('')
    print('check-skills: %d/%d skills are valid' % (len(roots) - bad, len(roots)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
