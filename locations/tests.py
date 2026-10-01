from unittest.mock import patch
from django.core.cache import cache
from django.test import TestCase
from .models import County,SensitiveLocation,Ward
from .services import resolve_report_location


class LocationResolutionTests(TestCase):
    def setUp(self):
        cache.clear(); self.county=County.objects.create(name="Mombasa",code="001")
        self.ward=Ward.objects.create(county=self.county,name="Likoni")
        SensitiveLocation.objects.create(name="Demo beach",location_type="beach",county=self.county,latitude=-4.0901,longitude=39.6601,protection_radius_m=500)

    @patch("locations.services._fetch_reverse_geocode")
    def test_resolves_configured_county_ward_and_water_distance(self,fetch):
        fetch.return_value={"display_name":"Likoni, Mombasa County, Kenya","address":{"country_code":"ke","county":"Mombasa County","suburb":"Likoni Ward"}}
        result=resolve_report_location(-4.09,39.66)
        self.assertEqual(result["county"],self.county); self.assertEqual(result["ward"],self.ward)
        self.assertEqual(result["proximity_to_water"],"under_50")

    @patch("locations.services._fetch_reverse_geocode")
    def test_resolves_kenyan_state_and_locality_alias_to_ward(self, fetch):
        taita = County.objects.get(name="Taita Taveta")
        ronge = Ward.objects.get(county=taita, name="Ronge")
        fetch.return_value = {
            "display_name": "Mariwenyi, Voi, Taita Taveta, Kenya",
            "address": {
                "country_code": "ke",
                "village": "Mariwenyi",
                "county": "Voi",
                "state": "Taita Taveta",
            },
        }

        result = resolve_report_location(-3.4181, 38.508956)

        self.assertEqual(result["county"], taita)
        self.assertEqual(result["ward"], ronge)

    @patch("locations.services._fetch_reverse_geocode")
    def test_resolves_msau_locality_to_ronge_ward(self, fetch):
        taita = County.objects.get(name="Taita Taveta")
        ronge = Ward.objects.get(county=taita, name="Ronge")
        fetch.return_value = {
            "display_name": "D538, Msau, Wundanyi, Taita Taveta, Kenya",
            "address": {
                "country_code": "ke",
                "village": "Msau",
                "county": "Wundanyi",
                "state": "Taita Taveta",
            },
        }

        result = resolve_report_location(-3.406575, 38.384342)

        self.assertEqual(result["county"], taita)
        self.assertEqual(result["ward"], ronge)
