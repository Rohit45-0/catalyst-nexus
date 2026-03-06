"""
Geo Parser
===========

Parses IP addresses to get geographic location data.
"""

import requests


class GeoParser:
    """Parses geographic data from IP addresses."""

    @staticmethod
    def get_city_country(ip_address: str) -> tuple[str, str]:
        """Get city and country from IP address.

        Args:
            ip_address: The IP address to geolocate

        Returns:
            Tuple of (city, country) or ("Unknown", "Unknown") if not found
        """
        try:
            # Using ipapi.co for free geolocation
            response = requests.get(f"http://ipapi.co/{ip_address}/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                city = data.get('city', 'Unknown')
                country = data.get('country_name', 'Unknown')
                return city, country
        except Exception:
            pass

        return "Unknown", "Unknown"