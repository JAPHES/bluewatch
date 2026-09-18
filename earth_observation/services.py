from abc import ABC, abstractmethod


def point_in_polygon(latitude, longitude, boundary):
    """Return whether a point is inside a simple GeoJSON polygon outer ring."""
    x, y = float(longitude), float(latitude)
    ring = boundary["coordinates"][0]
    inside = False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = float(point[0]), float(point[1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        crosses = (yi > y) != (yj > y)
        if crosses and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


class EarthObservationProvider(ABC):
    """Contract for a future validated satellite-analysis provider."""

    @abstractmethod
    def submit(self, survey):
        """Submit an AOI and return a provider job identifier."""

    @abstractmethod
    def collect(self, survey):
        """Return provider candidates with provenance, never verified reports."""


class NoProviderConfigured(EarthObservationProvider):
    def submit(self, survey):
        raise RuntimeError("No automated earth-observation provider is configured.")

    def collect(self, survey):
        raise RuntimeError("No automated earth-observation provider is configured.")


def get_provider():
    return NoProviderConfigured()
