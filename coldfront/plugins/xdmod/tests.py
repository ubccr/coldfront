"""Testing suite for the xdmod plugin."""
import json
import xml.etree.ElementTree as ET
from unittest import mock
from unittest.mock import patch, Mock

from django.test import TestCase

from coldfront.plugins.xdmod.utils import XDModFetcher, XdmodNotFoundError, XdmodError

XDMOD_XML_SIMPLE = """<xdmod-xml-dataset>
<header>
<title>CPU Hours: Total: by PI</title>
<parameters>
<parameter>
<name>PI </name>
<value> smith_lab</value>
</parameter>
</parameters>
<start>2023-09-01</start>
<end>2023-12-01</end>
<columns>
<column>PI</column>
<column>CPU Hours: Total</column>
</columns>
</header>
<rows>
<row>
<cell>
<value>smith_lab</value>
</cell>
<cell>
<value>720.1442</value>
</cell>
</row>
</rows>
</xdmod-xml-dataset>"""

def read_in_xml(xml):
    """Read in the xml."""
    root = ET.fromstring(xml)
    return root.find('rows')


class XDModFetcherTestCase(TestCase):
    """Tests for the xdmod plugin."""

    def setUp(self):
        """Set up the test case."""
        self.xdmodfetcher = XDModFetcher()
        # if the return value is valid xml, return the xml
        mock_response = Mock(text=XDMOD_XML_SIMPLE)
        mock_response.json.side_effect = json.decoder.JSONDecodeError('JSON decode error', '', 0)
        self.correct_return_value = mock_response

    @mock.patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_fetch_data(self, mock_get):
        """Test that the fetcher works."""
        # if the return value is not xml, raise an exception
        mock_get.return_value = Mock(text="Hello")
        with self.assertRaises(XdmodError):
            self.xdmodfetcher.fetch_data(None)
        # if the return value is empty xml, raise an exception
        mock_get.return_value = Mock(text="<xml></xml>")
        with self.assertRaises(XdmodNotFoundError):
            self.xdmodfetcher.fetch_data(None)
        mock_get.return_value = self.correct_return_value
        actual_result = ET.tostring(self.xdmodfetcher.fetch_data(None)).decode()
        self.assertEqual(actual_result, ET.tostring(read_in_xml(XDMOD_XML_SIMPLE)).decode())

    @mock.patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_fetch_value(self, mock_get):
        """Test that fetch_value works."""
        mock_get.return_value = self.correct_return_value
        self.assertEqual(self.xdmodfetcher.fetch_value(None), '720.1442')

    @mock.patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_fetch_value_error(self, mock_get):
        """Test that fetch_value raises an exception if the xml is invalid."""
        mock_get.return_value = Mock(status_code=200, text="<xml><data><row><cell>no_second_value</cell></row></data></xml>")
        with self.assertRaises(XdmodError):
            self.xdmodfetcher.fetch_value(None)

    @mock.patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_fetch_table(self, mock_get):
        """Test that fetch_table works."""
        mock_get.return_value = self.correct_return_value
        self.assertEqual(self.xdmodfetcher.fetch_table(None), {"smith_lab": '720.1442'})

    @mock.patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_fetch_table_error(self, mock_get):
        """Test that fetch_table raises an exception if the xml is invalid."""
        mock_get.return_value = Mock(status_code=200, text="<xml><data><row><cell>no_second_value</cell></row></data></xml>")
        with self.assertRaises(XdmodError):
            self.xdmodfetcher.fetch_table(None)

    @mock.patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_xdmod_fetch(self, mock_get):
        """Test that xdmod_fetch works."""
        mock_get.return_value = self.correct_return_value
        self.assertEqual(self.xdmodfetcher.xdmod_fetch("account", "statistic", "realm"), '720.1442')

    @patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_xdmod_fetch_all_project_usages(self, mock_get):
        mock_get.return_value = self.correct_return_value
        self.assertEqual(self.xdmodfetcher.xdmod_fetch_all_project_usages("statistic"), {"smith_lab": '720.1442'})

    @patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_xdmod_fetch_cpu_hours(self, mock_get):
        mock_get.return_value = self.correct_return_value
        self.assertEqual(self.xdmodfetcher.xdmod_fetch_cpu_hours("account", group_by='total', statistics='total_cpu_hours'), '720.1442')

    @patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_xdmod_fetch_storage(self, mock_get):
        mock_get.return_value = self.correct_return_value
        self.assertEqual(self.xdmodfetcher.xdmod_fetch_storage("account", group_by='total', statistic='physical_usage'), 720.1442 / 1E9)

    @patch("coldfront.plugins.xdmod.utils.requests.get")
    def test_xdmod_fetch_cloud_core_time(self, mock_get):
        mock_get.return_value = self.correct_return_value
        self.assertEqual(self.xdmodfetcher.xdmod_fetch_cloud_core_time("project"), '720.1442')
