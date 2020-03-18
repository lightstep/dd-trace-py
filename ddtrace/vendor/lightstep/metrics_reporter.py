from os import environ

import backoff

from .constants import ACCESS_TOKEN_ENV_VAR

DEFAULT_METRICS_HOSTNAME = environ.get("LIGHTSTEP_METRICS_HOST", environ.get("LIGHTSTEP_HOST", "ingest.lightstep.com"))
DEFAULT_METRICS_PORT = environ.get("LIGHTSTEP_METRICS_PORT", environ.get("LIGHTSTEP_PORT", "443"))
DEFAULT_METRICS_SECURE = environ.get("LIGHTSTEP_METRICS_SECURE", environ.get("LIGHTSTEP_SECURE", "1"))
DEFAULT_METRICS_PATH = "/metrics"
TOKEN = environ.get(ACCESS_TOKEN_ENV_VAR, "INVALID_TOKEN")

DEFAULT_ACCEPT = "application/octet-stream"
DEFAULT_CONTENT_TYPE = "application/octet-stream"


class MetricsReporter:
    """ HTTP client to send data to Lightstep """

    def __init__(
        self,
        token=TOKEN,
        host=DEFAULT_METRICS_HOSTNAME,
        port=DEFAULT_METRICS_PORT,
        secure=DEFAULT_METRICS_SECURE,
        path=DEFAULT_METRICS_PATH,
    ):
        self._headers = {
            "Accept": DEFAULT_ACCEPT,
            "Content-Type": DEFAULT_CONTENT_TYPE,
            "Lightstep-Access-Token": token,
        }
        protocol = "https" if int(secure) else "http"
        self._url = "{}://{}:{}{}".format(protocol, host, port, path)

    @backoff.on_exception(backoff.expo, Exception, max_time=5)
    def send(self, content):

        import requests

        return requests.post(self._url, headers=self._headers, data=content)
