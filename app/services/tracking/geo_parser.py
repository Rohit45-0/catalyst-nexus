"""
Geo Parser
==========

Converts IP addresses to city/country without storing IP.
"""

import requests
from typing import Tuple, Optional


class GeoParser:
    """Parses IP to geo location."""
    
    @staticmethod
    def get_city_country(ip: str) -> Tuple[Optional[str], Optional[str]]:
        """Get city and country from IP using ip-api.com."""
        try:
            response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
            data = response.json()
            if data.get('status') == 'success':
                city = data.get('city')
                country = data.get('country')
                return city, country
        except Exception:
            pass
        return None, None