"""Publication configuration and credential-handling regression tests; no network."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import httpx
import pytest
from django.test import override_settings

from common.contracts import DomainError, timestamp
from forecasting.ml_client import call_service, get_metadata
from weather_archive.services import provider_forecast, VARIABLES
from windpower.configuration import service_url
from windpower.archive import fetch_archive, SITES

ROOT = Path(__file__).resolve().parents[1]
START = timestamp('2026-02-01T00:00:00Z')
TURBINE = Mock(latitude=43.6, longitude=78.5)


@pytest.mark.parametrize('value', ['', 'not-a-url', 'file:///private',
    'https://user:password@example.invalid/path', 'https://example.invalid/path?apikey=private',
    'https://example.invalid/path#secret', 'https://example.invalid:wrong/path',
    ' https://example.invalid/path', 'https://example.invalid/white space'])
def test_service_url_rejects_embedded_credentials_and_invalid_config(value):
    with pytest.raises(ValueError, match='Configure SERVICE_URL') as error:
        service_url(value, 'SERVICE_URL')
    assert 'password' not in str(error.value)
    assert 'private' not in str(error.value)


@override_settings(OPEN_METEO_FORECAST_URL='', OPEN_METEO_PREVIOUS_RUNS_URL='')
@pytest.mark.parametrize('live', [True, False])
def test_unconfigured_weather_does_not_call_any_service(live):
    with patch('weather_archive.services.requests.get') as request:
        with pytest.raises(DomainError) as error:
            provider_forecast(TURBINE, START, START - timedelta(hours=6), 'jma_gsm', live=live)
    assert error.value.code == 'weather_configuration'
    assert error.value.status == 503
    request.assert_not_called()


@override_settings(ML_BACKEND='http', ML_SERVICE_URL='', ML_METADATA_URL='')
def test_unconfigured_ml_has_no_hidden_service_or_demo_fallback():
    with patch('forecasting.ml_client.requests.get') as request:
        with pytest.raises(DomainError) as error:
            get_metadata()
    assert error.value.code == 'ml_configuration'
    request.assert_not_called()


@override_settings(OPEN_METEO_FORECAST_URL='https://weather.example.invalid/v1/forecast',
                   OPEN_METEO_API_KEY='fixture-weather-credential')
def test_weather_key_sent_separately_but_not_persisted():
    hourly = {'time': [(START + timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(48)]}
    units = {}
    for field, variable in VARIABLES.items():
        hourly[variable] = [5] * 48
        units[variable] = {'wind_speed_10m_ms': 'm/s', 'wind_direction_10m_deg': '°', 'temperature_2m_c': '°C'}[field]
    response = Mock(status_code=200, json=lambda: {'hourly': hourly, 'hourly_units': units})
    with patch('weather_archive.services.requests.get', return_value=response) as request:
        records, provenance = provider_forecast(TURBINE, START, START, 'jma_gsm', live=True)
    assert request.call_args.kwargs['params']['apikey'] == 'fixture-weather-credential'
    assert request.call_args.kwargs['allow_redirects'] is False
    assert 'fixture-weather-credential' not in json.dumps(provenance)
    assert 'apikey' not in provenance['request_params']
    assert len(records) == 48


@override_settings(OPEN_METEO_FORECAST_URL='https://weather.example.invalid/v1/forecast', OPEN_METEO_API_KEY='fixture-weather-credential')
def test_weather_redirect_is_rejected_without_disclosing_url_or_key():
    with patch('weather_archive.services.requests.get', return_value=Mock(status_code=302)):
        with pytest.raises(DomainError) as error:
            provider_forecast(TURBINE, START, START, 'jma_gsm', live=True)
    assert error.value.code == 'weather_unavailable'
    assert 'fixture-weather-credential' not in str(error.value)


def test_ml_does_not_follow_redirects():
    with patch('forecasting.ml_client.requests.post', return_value=Mock(status_code=307)) as request:
        with pytest.raises(DomainError):
            call_service('POST', 'https://ml.example.invalid/v1/predict', {})
    assert request.call_args.kwargs['allow_redirects'] is False


def test_archive_requires_explicit_endpoint_before_creating_files(monkeypatch, tmp_path):
    monkeypatch.delenv('OPEN_METEO_PREVIOUS_RUNS_URL', raising=False)
    output = tmp_path / 'private' / 'weather.csv'
    with pytest.raises(ValueError, match='OPEN_METEO_PREVIOUS_RUNS_URL'):
        fetch_archive('2026-01-01', '2026-01-01', output)
    assert not output.parent.exists()


def test_archive_cache_and_manifest_never_store_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv('OPEN_METEO_PREVIOUS_RUNS_URL', 'https://archive.example.invalid/v1/forecast')
    monkeypatch.setenv('OPEN_METEO_API_KEY', 'fixture-archive-credential')
    hourly = {'time': [f'2026-01-01T{i:02d}:00' for i in range(24)]}
    for variable in VARIABLES.values():
        for offset in (1, 2):
            hourly[f'{variable}_previous_day{offset}'] = [5.0] * 24
    payload = [dict(latitude=lat, longitude=lon, hourly=copy.deepcopy(hourly)) for _, lat, lon in SITES]
    response = Mock(content=json.dumps(payload).encode())
    with patch('windpower.archive.httpx.get', return_value=response) as request:
        fetch_archive('2026-01-01', '2026-01-01', tmp_path / 'weather.csv')
    assert request.call_args.kwargs['params']['apikey'] == 'fixture-archive-credential'
    assert request.call_args.kwargs['follow_redirects'] is False
    for path in tmp_path.rglob('*'):
        if path.is_file():
            assert b'fixture-archive-credential' not in path.read_bytes()
    with patch('windpower.archive.httpx.get') as request:
        fetch_archive('2026-01-01', '2026-01-01', tmp_path / 'weather.csv')
    request.assert_not_called()


def test_archive_errors_do_not_expose_provider_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv('OPEN_METEO_PREVIOUS_RUNS_URL', 'https://archive.example.invalid/v1/forecast')
    with patch('windpower.archive.httpx.get', side_effect=httpx.ConnectError('private-upstream-value')), patch('windpower.archive.time.sleep'):
        with pytest.raises(RuntimeError) as error:
            fetch_archive('2026-01-01', '2026-01-01', tmp_path / 'weather.csv')
    assert 'private-upstream-value' not in str(error.value)
    assert error.value.__suppress_context__


def test_environment_template_keeps_secrets_and_external_endpoints_blank():
    config = dict(line.split('=', 1) for line in (ROOT / '.env.example').read_text().splitlines()
                  if line and not line.startswith('#'))
    for name in ('DJANGO_SECRET_KEY', 'API_TOKEN', 'ML_SERVICE_TOKEN', 'ML_SERVICE_URL',
                 'ML_METADATA_URL', 'OPEN_METEO_FORECAST_URL', 'OPEN_METEO_PREVIOUS_RUNS_URL',
                 'OPEN_METEO_API_KEY', 'WEATHER_PROVIDER_URL', 'WEATHER_PROVIDER_TOKEN'):
        assert config[name] == ''


def test_production_refuses_blank_secrets(monkeypatch):
    monkeypatch.setenv('DJANGO_DEBUG', '0')
    monkeypatch.delenv('DJANGO_SECRET_KEY', raising=False)
    monkeypatch.delenv('API_TOKEN', raising=False)
    result = subprocess.run([sys.executable, '-c', 'import config.settings'], cwd=ROOT,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert 'ImproperlyConfigured' in result.stderr


def test_publication_guard_redacts_credential_findings(tmp_path):
    value = 'gh' + 'p_' + 'a' * 36
    (tmp_path / 'config.txt').write_text(value)
    result = subprocess.run([sys.executable, str(ROOT / 'tools/check_publication.py'), '--root', str(tmp_path)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 1
    assert 'github-token' in result.stdout
    assert value not in result.stdout


def test_publication_guard_rejects_private_input_files(tmp_path):
    (tmp_path / 'dataset.csv').write_text('private-input')
    result = subprocess.run([sys.executable, str(ROOT / 'tools/check_publication.py'), '--root', str(tmp_path)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 1
    assert 'private-or-local-file' in result.stdout


@pytest.mark.parametrize('variant,expected_rule', [
    ('reviewed', None),
    ('changed', 'reviewed-binary-changed'),
    ('unlisted', 'unreviewed-binary'),
])
def test_publication_guard_only_accepts_exact_reviewed_screenshot(tmp_path, variant, expected_rule):
    relative = Path('docs/images/arys-top-125-960x720.png')
    content = (ROOT / relative).read_bytes()
    assert content[:8] == b'\x89PNG\r\n\x1a\n'
    assert int.from_bytes(content[16:20], 'big') == 960
    assert int.from_bytes(content[20:24], 'big') == 720
    destination = tmp_path / (relative if variant != 'unlisted' else 'other.png')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content + b'unreviewed-change' if variant == 'changed' else content)
    result = subprocess.run([sys.executable, str(ROOT / 'tools/check_publication.py'), '--root', str(tmp_path)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == (1 if expected_rule else 0)
    if expected_rule:
        assert expected_rule in result.stdout
    else:
        assert 'findings: 0' in result.stdout
