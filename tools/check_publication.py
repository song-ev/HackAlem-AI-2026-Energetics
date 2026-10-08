"""Lightweight publication guard; prints file/rule only, never secret values.

Checks tracked and non-ignored files when Git is available, otherwise a clean
source directory. This guard complements, but does not replace, Gitleaks and
manual review. It does not inspect dependencies or authenticate with services.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess

SKIP_DIRS = {'.git', '.venv', '__pycache__', '.pytest_cache', 'output', 'data',
             'artifacts', 'build', 'dist', 'staticfiles', '.ruff_cache', 'htmlcov'}
RULES = {
    'private-key': re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    'github-token': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'service-key': re.compile(r'(?:nvapi-[A-Za-z0-9_-]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{15,})'),
    'url-credentials': re.compile(r'https?://[^\s/]+:[^\s/]+@'),
    'personal-path': re.compile(r'(?:[A-Z]:[/\\]+Users[/\\]+[A-Za-z0-9_.-]+|/home/[A-Za-z0-9_.-]+)', re.I),
}
BLANK_CONFIG = {'DJANGO_SECRET_KEY', 'API_TOKEN', 'ML_SERVICE_TOKEN', 'ML_SERVICE_URL',
                'ML_METADATA_URL', 'OPEN_METEO_FORECAST_URL', 'OPEN_METEO_PREVIOUS_RUNS_URL',
                'OPEN_METEO_API_KEY', 'WEATHER_PROVIDER_URL', 'WEATHER_PROVIDER_TOKEN'}


def source_files(root):
    if (root / '.git').exists():
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                                capture_output=True, check=True)
        return sorted({root / p for p in result.stdout.decode('utf-8').split('\0') if p})
    files = []
    for directory, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith('.egg-info')]
        files.extend(Path(directory) / name for name in names)
    return sorted(files)


def scan(root):
    findings = []
    files = source_files(root)
    for path in files:
        relative = path.relative_to(root).as_posix()
        if not path.is_file():
            continue
        name = path.name.lower()
        if (name.startswith('.env') and name != '.env.example') or path.suffix.lower() in {
                '.pem', '.key', '.p12', '.pfx', '.sqlite3', '.csv', '.parquet', '.docx', '.pdf'}:
            findings.append((relative, 'private-or-local-file'))
        if path.is_symlink():
            findings.append((relative, 'unexpected-symlink'))
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeError:
            findings.append((relative, 'unreviewed-binary'))
            continue
        # Tests intentionally contain fake credentials and negative URL fixtures.
        if not relative.startswith('tests/') and relative != 'tools/check_publication.py':
            for rule, pattern in RULES.items():
                if pattern.search(content):
                    findings.append((relative, rule))
        if name == '.env.example':
            values = dict(line.split('=', 1) for line in content.splitlines() if '=' in line and not line.startswith('#'))
            for key in BLANK_CONFIG:
                if values.get(key) != '':
                    findings.append((relative, 'blank-required:' + key))
    return files, findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    files, findings = scan(args.root.resolve())
    for path, rule in findings:
        print(f'{path}: {rule}')
    print(f'Checked {len(files)} publication files; findings: {len(findings)}. Also run Gitleaks before pushing.')
    return int(bool(findings))


if __name__ == '__main__':
    raise SystemExit(main())
