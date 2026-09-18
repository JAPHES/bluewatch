from django.conf import settings


def map_configuration(request):
    """Expose public browser-safe basemap configuration to templates."""
    return {
        "map_tile_url": settings.MAP_TILE_URL,
        "map_tile_attribution": settings.MAP_TILE_ATTRIBUTION,
        "satellite_tile_url": settings.SATELLITE_TILE_URL,
        "satellite_tile_attribution": settings.SATELLITE_TILE_ATTRIBUTION,
    }
