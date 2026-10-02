"""Tests for waypoint parsing, distance calculations, and clockwise ordering."""

from dataclasses import FrozenInstanceError

import pytest

from src.types import Coordinate
from src.waypoint_utils import (
    east_north_coordinate_offset_m,
    parse_waypoints_file,
    sort_clockwise_sweep,
)


def write_to_tmp_waypoints_file(tmp_path, text):
    path = tmp_path / "waypoints.yaml"
    path.write_text(text)
    return path


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            (
                "home: {lat: 1, lon: 2, alt: 3}\n"
                "waypoints:\n  - {lat: 4, lon: 5, alt: 6}\n"
            ),
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
        (
            (
                "waypoints:\n"
                "  - {lat: 4, lon: 5, alt: 6}\n"
                "  - {lat: 7, lon: 8, alt: 9}\n"
            ),
            (None, [Coordinate(4, 5, 6), Coordinate(7, 8, 9)]),
        ),
        (
            (
                "# a lap\n\nhome: {lat: 1, lon: 2, alt: 3}\n\n"
                "waypoints:\n  # first leg\n  - {lat: 4, lon: 5, alt: 6}\n"
            ),
            (Coordinate(1, 2, 3), [Coordinate(4, 5, 6)]),
        ),
    ],
    ids=["home-and-waypoints", "no-home", "comments-and-blank-lines"],
)
def test_parse_waypoints_file_success(tmp_path, text, expected):
    path = write_to_tmp_waypoints_file(tmp_path, text)
    assert parse_waypoints_file(path) == expected


def test_empty_files_and_waypoint_lists(tmp_path):
    for text in ("", "waypoints: []", "{}"):
        path = write_to_tmp_waypoints_file(tmp_path, text)
        assert parse_waypoints_file(path) == (None, [])


def test_invalid_yaml_raises_value_error(tmp_path):
    path = write_to_tmp_waypoints_file(tmp_path, "waypoints: [")
    with pytest.raises(ValueError):
        parse_waypoints_file(path)


def test_missing_file_raises_os_error(tmp_path):
    with pytest.raises(OSError):
        parse_waypoints_file(tmp_path / "missing.yaml")


def test_malformed_waypoint_data_is_rejected(tmp_path):
    invalid_documents = [
        "- one\n- two\n",
        "waypoints: {lat: 1, lon: 2, alt: 3}",
        "waypoints: [not-a-mapping]",
        "home: not-a-mapping",
        "waypoints: [{lon: 2, alt: 3}]",
        "waypoints: [{lat: 1, alt: 3}]",
        "waypoints: [{lat: 1, lon: 2}]",
        "waypoints: [{lat: nope, lon: 2, alt: 3}]",
        "waypoints: [{lat: 1, lon: nope, alt: 3}]",
        "waypoints: [{lat: 1, lon: 2, alt: nope}]",
        "waypoints: [{lat: 91, lon: 2, alt: 3}]",
        "waypoints: [{lat: -91, lon: 2, alt: 3}]",
        "waypoints: [{lat: 1, lon: 181, alt: 3}]",
        "waypoints: [{lat: 1, lon: -181, alt: 3}]",
    ]
    for text in invalid_documents:
        path = write_to_tmp_waypoints_file(tmp_path, text)
        with pytest.raises(ValueError):
            parse_waypoints_file(path)


def test_east_north_coordinate_offset_m():
    assert east_north_coordinate_offset_m(0, 0, 0, 1) == pytest.approx(
        (111_195, 0), abs=2
    )
    assert east_north_coordinate_offset_m(0, 0, 1, 0) == pytest.approx(
        (0, 111_195), abs=2
    )
    assert east_north_coordinate_offset_m(60, 0, 60, 1) == pytest.approx(
        (55_598, 0), abs=2
    )
    assert east_north_coordinate_offset_m(0, 0, -1, 0) == pytest.approx(
        (0, -111_195), abs=2
    )


def test_sort_empty_and_single_waypoint():
    assert sort_clockwise_sweep([]) == []

    waypoint = Coordinate(1, 2, 3)
    original = [waypoint]
    result = sort_clockwise_sweep(original)

    assert result == original
    assert result is not original


def test_sort_clockwise_from_north():
    north = Coordinate(1, 0, 10)
    east = Coordinate(0, 1, 10)
    south = Coordinate(-1, 0, 10)
    west = Coordinate(0, -1, 10)

    original = [south, west, east, north]
    assert sort_clockwise_sweep(original) == [north, east, south, west]
    assert original == [south, west, east, north]


def test_sort_starts_in_home_direction():
    north = Coordinate(1, 0, 10)
    east = Coordinate(0, 1, 10)
    south = Coordinate(-1, 0, 10)
    west = Coordinate(0, -1, 10)
    home = Coordinate(0, 2, 10)

    assert sort_clockwise_sweep([west, north, south, east], home) == [
        east, south, west, north
    ]


def test_home_at_centroid_starts_from_north():
    north = Coordinate(1, 0, 10)
    east = Coordinate(0, 1, 10)
    south = Coordinate(-1, 0, 10)
    west = Coordinate(0, -1, 10)
    home = Coordinate(0, 0, 10)

    assert sort_clockwise_sweep([west, south, north, east], home) == [
        north, east, south, west
    ]


def test_same_bearing_closer_waypoint_comes_first():
    near = Coordinate(1, 0, 10)
    far = Coordinate(2, 0, 10)
    south = Coordinate(-3, 0, 10)

    assert sort_clockwise_sweep([far, south, near]) == [near, far, south]


def test_parsed_coordinates_are_frozen(tmp_path):
    text = (
        "home: {lat: 1, lon: 2, alt: 3}\n"
        "waypoints: [{lat: 4, lon: 5, alt: 6}]"
    )
    path = write_to_tmp_waypoints_file(tmp_path, text)
    home, waypoints = parse_waypoints_file(path)

    assert home is not None
    for coordinate in [home, *waypoints]:
        with pytest.raises(FrozenInstanceError):
            coordinate.lat = 99