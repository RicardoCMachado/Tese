from src.models.alert import Coordinates, FireAlert, RadioStation
from src.models.config import ServerConfig
from src.services.transmission_service import TransmissionService


def test_legacy_payload_uses_real_station_data():
    config = ServerConfig(simulation_mode=True)
    service = TransmissionService(config)

    alert = FireAlert(alert_id="A1", coordinates=Coordinates(40.0, -8.0))
    alert.nearby_stations = [
        RadioStation(
            ps="RFM",
            pi="8400",
            frequency=89.9,
            latitude=40.0,
            longitude=-8.0,
            coverage_radius=10.0,
        )
    ]

    payload = service.build_legacy_payload(alert, b"WAV")
    assert payload.startswith(b"WAV")
    assert b"PS=RFM;" in payload
    assert b"PI=8400;" in payload
    assert b"AF=89.9;" in payload


def test_legacy_payload_fallback_values_when_no_station():
    config = ServerConfig(simulation_mode=True)
    service = TransmissionService(config)
    alert = FireAlert(alert_id="A2", coordinates=Coordinates(40.0, -8.0))

    payload = service.build_legacy_payload(alert, b"WAV")
    assert b"PS=FIRETEC1;" in payload
    assert b"PI=8400;" in payload
    assert b"AF=100.0,102.0;" in payload
