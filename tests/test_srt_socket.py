import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import srt_socket


class TestParseUrlForRunhash:
    def test_full_share_url(self):
        url = (
            "https://ttsview.railway.co.th/v3/search/?qType=21"
            "&qParam=dqhu9zQKw0omVC75lP7lGTRu3nZ2mb72CGde"
            "&auth=fcac9512ab931c47589c9bad099ccb3d4b4c4dcf5aca791c366cdb2df068cc5d1778289391"
        )
        assert srt_socket.parse_url_for_runhash(url) == "dqhu9zQKw0omVC75lP7lGTRu3nZ2mb72CGde"

    def test_url_with_whitespace(self):
        url = "  https://ttsview.railway.co.th/v3/search/?qType=21&qParam=abcdef1234567890xyz  "
        assert srt_socket.parse_url_for_runhash(url) == "abcdef1234567890xyz"

    def test_no_qparam_returns_none(self):
        assert srt_socket.parse_url_for_runhash("https://ttsview.railway.co.th/v3/") is None

    def test_short_qparam_rejected(self):
        url = "https://ttsview.railway.co.th/v3/search/?qType=21&qParam=tiny"
        assert srt_socket.parse_url_for_runhash(url) is None

    def test_invalid_url_returns_none(self):
        assert srt_socket.parse_url_for_runhash("not a url at all") is None

    def test_empty_string(self):
        assert srt_socket.parse_url_for_runhash("") is None


@pytest.mark.integration
def test_fetch_train_stations_live():
    """Live integration: requires that today's runhash is reachable. Skipped by default."""
    runhash = os.environ.get("SRT_TEST_RUNHASH")
    if not runhash:
        pytest.skip("Set SRT_TEST_RUNHASH to run this integration test")
    stations = srt_socket.fetch_train_stations(runhash, timeout=20)
    assert isinstance(stations, list)
    assert len(stations) > 0
    first = stations[0]
    assert "stop_name" in first
    assert "def_arrtime" in first
