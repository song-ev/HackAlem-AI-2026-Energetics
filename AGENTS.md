# Repository development

- Work from this repository root. Do not hardcode a contributor's local path.
- Backend: Django and separate FastAPI inference. Frontend: native HTML/CSS/JavaScript.
- Configure external endpoints and credentials through environment variables. Keep secrets and external URLs blank in `.env.example`.
- Never replace archived forecasts with observations/reanalysis or hide service failures with demo predictions.
- Keep `alignment_confirmed` and weather-availability limitations visible. Do not edit weights to bypass safeguards.
- Preserve the ML contract in `docs/ML_INTEGRATION.md` and tests for both turbines.
- Keep private datasets, database files, credentials, logs and generated artifacts out of Git.
- Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python -m pytest -q`, and `python tools/check_publication.py` before release.
- Use Python 3.12 and a repository-local `.venv`. Training dependencies are optional for runtime but required for the full test suite.
