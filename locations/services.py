from math import asin, cos, radians, sin, sqrt

def distance_km(lat1, lon1, lat2, lon2):
    """Haversine distance; adequate for MVP proximity checks."""
    lat1, lon1, lat2, lon2 = map(lambda v: radians(float(v)), (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 6371.0088 * 2 * asin(sqrt(a))

