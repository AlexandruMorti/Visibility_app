import os
import typing as t
import requests

KNOT_TO_MS = 0.514444

Proxies = t.Dict[str, str]


def _get_proxies() -> Proxies:
    proxies: Proxies = {}
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy
    return proxies


def _get_verify() -> t.Union[bool, str]:
    """Determine SSL verification setting.
    RESPECTS:
    - WEATHER_VERIFY: 'false'/'0' disables verification (testing only)
    - REQUESTS_CA_BUNDLE or SSL_CERT_FILE: path to CA bundle
    Defaults to True.
    """
    verify_env = (os.environ.get("WEATHER_VERIFY") or "").strip().lower()
    if verify_env in {"false", "0", "no"}:
        return False
    # Prefer REQUESTS_CA_BUNDLE, then SSL_CERT_FILE
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    return ca_bundle if ca_bundle else True


def get_current_weather(lat: float, lon: float, timeout: int = 15) -> dict:
    """
    Fetch current weather from Open-Meteo.
    Returns dict with keys: time, temperature_2m, wind_speed_knots, wind_speed_ms, wind_direction_10m.
    """
    params = {
        "latitude": float(lat),
        "longitude": float(lon),
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "kn",  # request knots directly
    }
    # Bypass proxy - use empty dict to force direct connection
    proxies = {}
    verify = _get_verify()
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params=params,
        timeout=timeout,
        proxies=proxies,
        verify=False,  # Insecure: bypass SSL certificate validation
    )
    r.raise_for_status()
    j = r.json()
    current = j.get("current", {})
    wind_knots = current.get("wind_speed_10m")
    wind_ms = float(wind_knots) * KNOT_TO_MS if wind_knots is not None else None
    return {
        "time": current.get("time"),
        "temperature_2m": current.get("temperature_2m"),
        "wind_speed_knots": wind_knots,
        "wind_speed_ms": wind_ms,
        "wind_direction_10m": current.get("wind_direction_10m"),
        "raw": current,
    }

