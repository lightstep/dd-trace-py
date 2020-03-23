from os import environ

import backoff

from .constants import ACCESS_TOKEN_ENV_VAR, METRICS_URL_ENV_VAR


DEFAULT_METRICS_URL = environ.get(METRICS_URL_ENV_VAR, "https://ingest.lightstep.com:443/metrics")
TOKEN = environ.get(ACCESS_TOKEN_ENV_VAR, "INVALID_TOKEN")

DEFAULT_ACCEPT = "application/octet-stream"
DEFAULT_CONTENT_TYPE = "application/octet-stream"


class MetricsReporter:
    """ HTTP client to send data to Lightstep """

    def __init__(
        self,
        token=TOKEN,
        url=DEFAULT_METRICS_URL,
    ):
        self._headers = {
            "Accept": DEFAULT_ACCEPT,
            "Content-Type": DEFAULT_CONTENT_TYPE,
            "Lightstep-Access-Token": token,
        }
        self._url = url

    @backoff.on_exception(backoff.expo, Exception, max_time=5)
    def send(self, content, token=None):

        if token is not None:
            self._headers["Lightstep-Access-Token"] = token

        import requests

        return requests.post(self._url, headers=self._headers, data=content)
