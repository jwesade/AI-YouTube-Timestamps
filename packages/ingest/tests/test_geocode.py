from __future__ import annotations

from ingest.geocode import ReverseResult, parse_nominatim_response


def test_parse_nominatim_city_and_postcode():
    payload = {
        "address": {
            "road": "Hauptstraße",
            "house_number": "12a",
            "postcode": "10115",
            "city": "Berlin",
            "country_code": "de",
        }
    }
    result = parse_nominatim_response(payload)
    assert result == ReverseResult(
        address="Hauptstraße 12a",
        city="Berlin",
        postal_code="10115",
        country="DE",
    )


def test_parse_falls_back_through_locality_levels():
    payload = {
        "address": {
            "road": "Dorfstraße",
            "postcode": "12345",
            "village": "Neuhausen",
            "country_code": "de",
        }
    }
    result = parse_nominatim_response(payload)
    assert result is not None
    assert result.city == "Neuhausen"
    assert result.address == "Dorfstraße"


def test_parse_empty_or_broken_payload():
    assert parse_nominatim_response(None) is None
    assert parse_nominatim_response({}) is None
    assert parse_nominatim_response({"address": "string-not-dict"}) is None


def test_parse_missing_street_returns_none_address():
    payload = {
        "address": {
            "postcode": "10115",
            "city": "Berlin",
            "country_code": "de",
        }
    }
    result = parse_nominatim_response(payload)
    assert result is not None
    assert result.address is None
    assert result.city == "Berlin"
