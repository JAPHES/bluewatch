import json
import re
from math import asin, cos, radians, sin, sqrt
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from .models import County, SensitiveLocation, Ward

def distance_km(lat1, lon1, lat2, lon2):
    """Haversine distance; adequate for MVP proximity checks."""
    lat1, lon1, lat2, lon2 = map(lambda v: radians(float(v)), (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 6371.0088 * 2 * asin(sqrt(a))


class LocationResolutionError(Exception):
    pass


def _normalise_place(value):
    value = re.sub(r"\b(county|ward|sub-county|subcounty)\b", "", value or "", flags=re.I)
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _match_named(queryset, candidates):
    cleaned = [_normalise_place(value) for value in candidates if value]
    for item in queryset:
        name = _normalise_place(item.name)
        if any(name == candidate or name in candidate or candidate in name for candidate in cleaned if candidate):
            return item
    return None


def _fetch_reverse_geocode(latitude, longitude):
    params = urlencode({"format": "jsonv2", "lat": latitude, "lon": longitude, "zoom": 18, "addressdetails": 1, "layer": "address"})
    contact = settings.REVERSE_GEOCODER_CONTACT.strip()
    user_agent = f"BlueWatch/1.0 ({contact})" if contact else "BlueWatch/1.0 (+https://github.com/JAPHES/bluewatch)"
    request = Request(f"{settings.REVERSE_GEOCODER_URL}?{params}", headers={"User-Agent": user_agent, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LocationResolutionError("The location service is temporarily unavailable. Please try again.") from exc


def resolve_report_location(latitude, longitude):
    """Resolve an internal county/ward and water proximity for a public map point."""
    latitude, longitude = float(latitude), float(longitude)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise LocationResolutionError("Select a valid point on the map.")
    cache_key = f"reverse-location:{latitude:.5f}:{longitude:.5f}"
    result = cache.get(cache_key)
    if result is None:
        if not cache.add("reverse-geocoder-request-lock", True, 1):
            raise LocationResolutionError("Location detection is busy. Please wait a moment and try again.")
        result = _fetch_reverse_geocode(latitude, longitude)
        cache.set(cache_key, result, 24 * 60 * 60)
    address = result.get("address") or {}
    if address.get("country_code", "").lower() != "ke":
        raise LocationResolutionError("BlueWatch reporting is currently limited to configured locations in Kenya.")
    county = _match_named(County.objects.filter(is_active=True), [address.get(key) for key in ("county", "state_district", "state", "region", "city")])
    if not county:
        raise LocationResolutionError("The detected county is not configured in BlueWatch.")
    ward = _match_named(Ward.objects.filter(county=county, is_active=True), [address.get(key) for key in ("suburb", "city_district", "district", "borough", "quarter", "neighbourhood", "municipality", "town", "village")])
    if not ward:
        raise LocationResolutionError("The detected ward is not configured in BlueWatch. Ask an administrator to add it.")
    water_types = {SensitiveLocation.Type.RIVER, SensitiveLocation.Type.DRAIN, SensitiveLocation.Type.BEACH, SensitiveLocation.Type.MANGROVE, SensitiveLocation.Type.WETLAND, SensitiveLocation.Type.MPA}
    water_locations = SensitiveLocation.objects.filter(is_active=True, location_type__in=water_types).filter(Q(county=county) | Q(county__isnull=True))
    nearest = None
    for place in water_locations:
        distance = distance_km(latitude, longitude, place.latitude, place.longitude)
        if nearest is None or distance < nearest[0]: nearest = (distance, place)
    if not nearest:
        proximity, water_label = "unknown", "No registered water location nearby"
    elif nearest[0] <= 0.05:
        proximity, water_label = "under_50", f"Within 50 m of {nearest[1].name}"
    elif nearest[0] <= 0.2:
        proximity, water_label = "under_200", f"Within 200 m of {nearest[1].name}"
    else:
        proximity, water_label = "over_200", f"More than 200 m from {nearest[1].name}"
    return {"county": county, "ward": ward, "location_description": (result.get("display_name") or f"{ward.name}, {county.name}")[:255], "proximity_to_water": proximity, "water_label": water_label}

