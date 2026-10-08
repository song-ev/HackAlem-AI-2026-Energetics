# Security and publication

This is a hackathon prototype, not a hardened public service. Keep it bound to
loopback for local use. Before an external deployment, configure authentication,
HTTPS, a production WSGI/ASGI server, request limits, static files and backups.

## Configuration

- Set your own `DJANGO_SECRET_KEY`, `API_TOKEN` and `ML_SERVICE_TOKEN` outside Git.
- `API_TOKEN` authenticates incoming Django requests; `ML_SERVICE_TOKEN` is the
  separate shared Django-to-ML credential. Neither is an NVIDIA key.
- External weather and ML URLs are blank by default. Configure only trusted
  destinations. Forecast requests disclose turbine coordinates and dates to the
  chosen weather provider. Do not publish service addresses with embedded credentials.
- `OPEN_METEO_API_KEY` is sent only to the configured provider. Its query value is
  excluded from stored request metadata. HTTP clients do not follow redirects in
  the main Django-to-ML/weather path and training archive downloader.
- No production signing secret is supplied. In local debug mode, a missing
  Django secret is generated per process; restarting invalidates existing sessions.
- Python does not automatically read `.env`. See README for environment exports.

Never commit `.env`, credential stores, private keys, database files, raw datasets,
weather caches, training job receipts, logs or virtual environments. Do not send
API keys in issue descriptions, screenshots or error reports.

## Before every push

Run `python tools/check_publication.py`, inspect `git diff --cached`, and run a
dedicated scanner such as `gitleaks dir --redact .` and `gitleaks git --redact .`.
The built-in guard is a small pattern check, not a comprehensive security audit.
An ignored file is not removed from Git if it was already tracked.

If a real key was ever published, revoke/rotate it with its provider. Removing
the current file or making a new repository does not revoke the exposed key.
Report vulnerabilities through the repository owner's private reporting channel
when available; public reports must not include secrets or sensitive datasets.

See [publication review](docs/PUBLICATION_REVIEW.md) for this release's scope,
checks and remaining limitations.
