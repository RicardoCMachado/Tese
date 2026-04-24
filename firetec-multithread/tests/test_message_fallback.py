from src.models.alert import Coordinates, Location
from src.services.location_service import LocationService


def test_message_adds_zone_warning_when_no_roads():
    location = Location(
        freguesia="Cacia",
        concelho="Aveiro",
        distrito="Aveiro",
        coordinates=Coordinates(40.68, -8.63),
    )
    msg = LocationService.generate_alert_message(location, [])
    assert "Evite circular na zona afetada." in msg
