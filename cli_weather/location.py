import json
import logging
from typing import Dict, Tuple
import requests
import geopy
from geopy.geocoders import Nominatim
from .config import VARS, load_config, save_config
from .utils import CLIWeatherException, confirm, get_index

logger = logging.getLogger(__file__)

# === Location management functions === #
def load_locations(add_sensitive: bool = False) -> Dict:
    """Load combined sensitive, non sensitive."""
    logger.debug("Loading locations...")
    non_sensitive_locations = load_config().get("locations", {})
    sensitive_locations = {
        key: value for key, value in VARS.items()
        if is_valid_location(value)
    }
    locations = {**sensitive_locations, **non_sensitive_locations} if add_sensitive else non_sensitive_locations

    logger.debug("Locations loaded successfully.")
    return locations


def is_valid_location(value: str) -> bool:
    """Check if a given value is a valid coordinate for location."""
    try:
        logger.debug(f"Checking if '{value}' is valid location coordinate.")
        lat, lon = map(float, value.split(","))
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (ValueError, TypeError):
        return False


def get_location(addr: str = "me") -> Tuple[str, str, str] | Tuple[None, None, None]:
    """Get location by address or approximate current location."""
    geopy.adapters.BaseAdapter.session = requests.Session()

    if addr.lower() == "me":  # Handle current location separately
        logger.debug("Getting current location...")
        try:
            # Use IP-based geolocation to get approximate current location
            ip_geolocation_url = "https://ipinfo.io/json"
            response = requests.get(ip_geolocation_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            lat, lon = map(float, data["loc"].split(","))
            # Use reverse geocoding to refine location details
            geolocator = Nominatim(user_agent="weather_assistant", timeout=10)
            location = geolocator.reverse((lat, lon), exactly_one=True)
            if location:
                return location.address, lat, lon
            else:
                return "Approximate location based on IP", lat, lon
        except requests.exceptions.Timeout as e:
            logger.error(f"Error getting current location coordinate from IP, Connection timed out: {e}")
            raise CLIWeatherException("Failed to get your current location, Request timed out. Please check your network connection.")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Error getting current location coordinate from IP, Connection error: {e}")
            raise CLIWeatherException("Failed to get your current location, Network error. Please check your connection and try again.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error Getting current coordinate using ip, RequestException: {e}")
            raise CLIWeatherException("Failed to get your current location, Please try again later.")
        except geopy.exc.GeocoderTimedOut as e:
            logger.error(f"Error getting current location, Geocoding timed out: {e}")
            raise CLIWeatherException("Failed to get your current location, geocoding timed out. Please check your network connection.")
        except geopy.exc.GeocoderUnavailable as e:
            logger.error(f"Error getting current location, Geocoding service unavailable: {e}")
            raise CLIWeatherException("Geocoding service is unavailable. Please check your internet connection.")
        except Exception:
            raise

    else:  # Use Geopy for address-based geocoding
        logger.debug(f"Getting location for: {addr}")
        try:
            geolocator = Nominatim(user_agent="weather_assistant", timeout=10)
            location = geolocator.geocode(addr)
            if location:
                return location.address, location.latitude, location.longitude
            else:
                logger.error(f"Geolocator could not find location: '{addr}'")
                raise CLIWeatherException(f"Could not find location: '{addr}'")
        except geopy.exc.GeocoderTimedOut as e:
            logger.error(f"Geocoding timed out: {e}")
            raise CLIWeatherException("Could not find location, Geocoding timed out.")
        except geopy.exc.GeocoderUnavailable:
            logger.error(f"Geolocator could not find location: {addr}. Geocoding service unavailable.")
            raise CLIWeatherException("Geocoding service is unavailable. Please check your internet connection.")
        except Exception:
            raise
    return None, None, None


def get_location_input() -> Tuple[str, str]:
    """Get location name and coordinate from user."""
    try:
        while True:
            location_name = input("Enter location name: ")
            print("Enter comma separated coordinates Lat/Long (Deg), e.g., 1.599, 12.6168")
            coordinate = input("> ")
            if is_valid_location(coordinate) and confirm("Done?"):
                return (location_name, coordinate)
    except KeyboardInterrupt:
        raise


def save_location(location_name: str, coordinate: str) -> None:
    """Write location info into configuration file."""
    logger.debug(f"Saving location : {location_name}...")
    configuration = load_config()
    configuration.setdefault("locations", {})[location_name] = coordinate
    save_config(configuration)
    logger.debug(f"{location_name} location saved successfully.")


def choose_location(task: str = "", add_sensitive: bool = False) -> Tuple[str, Tuple[str, str]]:
    """Prompt the user to choose a location."""
    print(f"\nChoose a location {task}:")
    coordinates = load_locations( add_sensitive)
    for index, name in enumerate(coordinates, start=1):
        print(f"{index}. {name.title()}")

    index = get_index(coordinates)
    location_name = list(coordinates.keys())[index]
    lat, lon = coordinates[location_name].split(",")
    return location_name, (lat.strip(), lon.strip())


def search_location() -> None:
    """Let user search location by address and save."""
    search_query = input("Enter location to search: ")
    try:  # Catching custom exception early here to prevent getting out of manage locations menu early.
        address, lat, lon = get_location(search_query)
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    if all((address, lat, lon)):
        print(f"Address found: {address}")
        if confirm("Save this location?"):
            location_name = input("Enter a name for this location: ").strip() or address
            save_location(location_name, f"{lat}, {lon}")
            print(f"Location '{location_name}' saved successfully.")
    else:
        print("Location not found.")


def view_locations() -> None:
    """View non sensitive locations saved by the user."""
    locations = load_locations()
    if not locations:
        print("No locations foud. Please add one first.")
        return
    print("\nYour Locations:\n")
    for location_name, coordinate in locations.items():
        lat, lon = coordinate.split(",")
        print(f"""{location_name.title()}:
            latitude: {lat.strip()}
            longitude: {lon}""")


def add_location() -> None:
    """Add non-sensitive location to configuration file."""
    location_name, coordinate = get_location_input()
    if confirm(f"Save this location?\n {location_name}: {coordinate}"):
        save_location(location_name, coordinate)
        print(f"New location {location_name} saved successfully.")


def save_current_location() -> None:
    """Let user save current location."""

    try:  # Catching custom exception early here to prevent getting out of manage locations menu.
        current_addr, lat, lon = get_location()
    except CLIWeatherException as e:
        print(f"Error: {e}")
        return

    print(f"Current location: {current_addr}:\n\tlatitude: {lat}, longitude: {lon}")
    if confirm("Do you want to rename location address?"):
        current_addr = input("Enter new name for this location: ")
    if confirm("Save this location?"):
        config = load_config()
        config["locations"][current_addr] = f"{str(lat)}, {str(lon)}"
        save_config(config)
        print("Current location saved successfully.")


def delete_location() -> None:
    """Let user remove a non sensitive location from configuration."""
    location_name, _ = choose_location(task="to delete")
    if confirm(f"Are you sure you want to delete '{location_name}'?"):
            config = load_config()
            del config["locations"][location_name]
            save_config(config)
            print(f"\n'{location_name}' deleted successfully.")
