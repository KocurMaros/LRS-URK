"""Package metadata and public configuration tests."""

import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).parents[1]


def test_package_manifest_is_valid_xml():
    """The manifest is well-formed and names the intended package."""
    root = ET.parse(PACKAGE_ROOT / 'package.xml').getroot()
    assert root.findtext('name') == 'localization_sensor_sim'


def test_configured_rates_covariance_and_outage():
    """The assignment's public sensor contract is represented in YAML."""
    with (PACKAGE_ROOT / 'config' / 'sensors.yaml').open() as stream:
        document = yaml.safe_load(stream)
        parameters = document['sensor_simulator']['ros__parameters']
    assert parameters['gps_rate_hz'] == 5.0
    assert parameters['vo_rate_hz'] == 30.0
    assert parameters['gps_position_stddev'] == [0.6, 0.6, 0.9]
    assert parameters['required_gps_outage_s'] == 15.0
