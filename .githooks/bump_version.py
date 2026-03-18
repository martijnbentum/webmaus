import re
import subprocess
import sys
from pathlib import Path


PYPROJECT = Path('pyproject.toml')
VERSION_RE = re.compile(r"^version = ['\"](\d+)\.(\d+)\.(\d+)['\"]$", re.M)
VERSION_DIFF_RE = re.compile(r"^[+-]version = ['\"]\d+\.\d+\.\d+['\"]$")


def git(*args):
    return subprocess.run(['git', *args], check=True, text=True,
        capture_output=True).stdout


def staged_files():
    output = git('diff', '--cached', '--name-only', '--diff-filter=ACMR')
    return [line for line in output.splitlines() if line]


def only_staged_change_is_version_bump():
    files = staged_files()
    if files != ['pyproject.toml']:
        return False

    diff = git('diff', '--cached', '--unified=0', '--', 'pyproject.toml')
    relevant_lines = []
    for line in diff.splitlines():
        if line.startswith(('diff --git', 'index ', '--- ', '+++ ', '@@')):
            continue
        if not line or line[0] not in '+-':
            continue
        if not VERSION_DIFF_RE.match(line):
            return False
        relevant_lines.append(line)
    return len(relevant_lines) == 2


def bump_patch_version():
    text = PYPROJECT.read_text()
    match = VERSION_RE.search(text)
    if match is None:
        raise RuntimeError('Could not find version in pyproject.toml')

    major, minor, patch = (int(value) for value in match.groups())
    old_version = f'{major}.{minor}.{patch}'
    new_version = f'{major}.{minor}.{patch + 1}'
    updated_text = text.replace(
        f"version = '{old_version}'",
        f"version = '{new_version}'",
        1,
    )
    PYPROJECT.write_text(updated_text)
    subprocess.run(['git', 'add', 'pyproject.toml'], check=True)


def main():
    if not PYPROJECT.exists():
        return 0
    if not staged_files():
        return 0
    if only_staged_change_is_version_bump():
        return 0

    bump_patch_version()
    return 0


if __name__ == '__main__':
    sys.exit(main())
