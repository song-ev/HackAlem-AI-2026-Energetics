"""Configuration validation shared by the portal and standalone training tools."""
from urllib.parse import urlsplit


def service_url(value, variable):
    """Keep credentials out of URLs, error messages and provenance records."""
    message = f'Configure {variable} with an HTTP(S) endpoint without credentials, query or fragment.'
    try:
        parts = urlsplit(value)
        valid = (value == value.strip() and not any(c.isspace() for c in value)
                 and parts.scheme in ('http', 'https') and parts.hostname
                 and parts.username is None and parts.password is None
                 and not parts.query and not parts.fragment)
        # Reject malformed port numbers as configuration errors before any request.
        _ = parts.port
    except (ValueError, AttributeError, TypeError):
        valid = False
    if not valid:
        raise ValueError(message)
    return value
