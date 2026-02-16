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


def fetch_windguru_json(url: str, timeout: int = 15) -> dict:
    """
    Fetch JSON from Windguru or a compatible endpoint.
    The caller must provide a full URL that returns JSON.
    Corporate environments can set SSL_CERT_FILE/REQUESTS_CA_BUNDLE and HTTP(S)_PROXY.
    """
    proxies = _get_proxies()
    resp = requests.get(url, timeout=timeout, proxies=proxies)
    resp.raise_for_status()
    return resp.json()


def map_features(json_obj: dict) -> dict:
    """
    Map Windguru-style JSON to the app features.
    Expected keys (if available):
    - wind_speed_knots (knots)
    - wind_dir_deg (degrees)
    - swell_height_m (meters)
    - swell_period_s (seconds)
    - tide_height_m (meters)
    - turbidity (relative)
    Missing values will be set to None for server-side imputation/defaults.
    """
    def _get(*keys):
        for k in keys:
            if k in json_obj:
                return json_obj[k]
        return None

    wind_knots = _get("wind_speed_knots", "wind_knots", "wind_speed")
    wind_dir = _get("wind_dir_deg", "wind_dir", "wind_direction")
    swell_h = _get("swell_height_m", "swell_height")
    swell_p = _get("swell_period_s", "swell_period")
    tide_h = _get("tide_height_m", "tide_height")
    turbidity = _get("turbidity")

    # Convert wind to m/s if present
    wind_ms = None
    try:
        if wind_knots is not None:
            wind_ms = float(wind_knots) * KNOT_TO_MS
    except Exception:
        wind_ms = None

    return {
        "swell_height": _safe_float(swell_h),
        "swell_period": _safe_float(swell_p),
        "wind_speed": _safe_float(wind_ms),
        "wind_dir": _safe_float(wind_dir),
        "tide_height": _safe_float(tide_h),
        "turbidity": _safe_float(turbidity),
    }


def _safe_float(x: t.Any) -> t.Optional[float]:
    try:
        return None if x is None else float(x)
    except Exception:
        return None
