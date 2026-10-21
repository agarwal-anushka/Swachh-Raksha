import math

AT_SITE_M = 150   # within this distance of the registered site: "at site"
NEAR_M = 500      # up to this: "near site, check"; beyond: "far from site"


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp, dl = p2 - p1, math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def site_check(ev, gen) -> dict:
    """Compare where the photo was captured with the generator's registered location."""
    if ev is None or ev.latitude is None or ev.longitude is None:
        return {"site_status": "no_gps", "site_distance_m": None}
    if gen is None or gen.latitude is None or gen.longitude is None:
        return {"site_status": "no_site", "site_distance_m": None}
    d = round(haversine_m(ev.latitude, ev.longitude, gen.latitude, gen.longitude))
    return {"site_status": "at_site" if d <= AT_SITE_M else "near" if d <= NEAR_M else "far", "site_distance_m": d}
