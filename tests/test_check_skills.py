#!/usr/bin/env python3
"""Self-test for tools/check-skills.py.

A validator that only ever sees valid input is not a validator, so feed it
the shapes that break: a name that drifted from its directory, a missing
description, a missing front matter block, a BOM, and a skill directory
with no SKILL.md at all.

No third-party dependency: run with "python tests/test_check_skills.py".
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    'check_skills', ROOT / 'tools' / 'check-skills.py')
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

PASS = 0
FAIL = 0
def text_for(name, description='Do the one thing this skill is for.'):
    """A valid SKILL.md for a directory called `name`."""
    return ('---\n'
            'name: %s\n'
            'description: %s\n'
            '---\n'
            '\n'
            '# %s\n' % (name, description, name))


GOOD = text_for('my-skill')


def check(desc, ok, detail=''):
    global PASS, FAIL
    print('  [%s] %s' % ('PASS' if ok else 'FAIL', desc))
    if not ok:
        print('         %s' % detail)
    if ok:
        PASS += 1
    else:
        FAIL += 1


def skill(tmp, name, text, filename='SKILL.md'):
    d = pathlib.Path(tmp) / name
    d.mkdir(parents=True, exist_ok=True)
    if text is not None:
        (d / filename).write_text(text, encoding='utf-8', newline='')
    return d


def run_main(paths):
    """Run the CLI with the given paths; returns (status, stdout)."""
    out = io.StringIO()
    old = sys.argv
    sys.argv = ['check-skills.py'] + [str(p) for p in paths]
    try:
        with contextlib.redirect_stdout(out):
            status = checker.main()
    finally:
        sys.argv = old
    return status, out.getvalue()


def main():
    tmp = tempfile.mkdtemp(prefix='check-skills-')
    check('a valid skill passes', checker.check_skill(skill(tmp, 'my-skill', GOOD)) == [])
    check('a quoted description is accepted',
          checker.check_skill(skill(tmp, 'quoted', text_for(
              'quoted', '"Do the one thing."'))) == [])
    check('a name that drifted from the directory fails',
          bool(checker.check_skill(skill(tmp, 'other-dir', GOOD))))
    check('a missing description fails',
          bool(checker.check_skill(skill(tmp, 'nodesc', text_for('nodesc').replace(
              'description: Do the one thing this skill is for.\n', '')))))
    check('a missing front matter block fails',
          bool(checker.check_skill(skill(tmp, 'nofront', '# just a title\n'))))
    check('a BOM fails',
          bool(checker.check_skill(skill(tmp, 'bom', '\ufeff' + text_for('bom')))))
    check('a directory without SKILL.md fails',
          bool(checker.check_skill(skill(tmp, 'empty', None))))

    print('cli')
    empty_root = pathlib.Path(tmp) / 'empty-root'
    (empty_root / 'skills').mkdir(parents=True)
    status, out = run_main(['--root', empty_root])
    check('an empty skills/ tree is not an error', status == 0, out.strip())
    status, out = run_main([pathlib.Path(tmp) / 'my-skill'])
    check('the cli accepts a valid skill', status == 0, out.strip())
    status, out = run_main([pathlib.Path(tmp) / 'other-dir'])
    check('the cli rejects a broken skill',
          status == 1 and 'does not match' in out, out.strip())

    print('')
    print('RESULT: %d passed, %d failed' % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
