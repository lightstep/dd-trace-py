# dd-trace-py

[![CircleCI](https://circleci.com/gh/lightstep/dd-trace-py/tree/master.svg?style=svg)](https://circleci.com/gh/lightstep/dd-trace-py/tree/master)
[![Pyversions](https://img.shields.io/pypi/pyversions/ddtrace.svg?style=flat)](https://pypi.org/project/ddtrace/)
[![PypiVersions](https://img.shields.io/pypi/v/ddtrace.svg)](https://pypi.org/project/ddtrace/)
[![OpenTracing Badge](https://img.shields.io/badge/OpenTracing-enabled-blue.svg)](http://pypi.datadoghq.com/trace/docs/installation_quickstart.html#opentracing)

If your app is written in Python, you can auto-instrument using our agent, without needing to add code to any of your services. Simply install the agent, configure it to communicate with LightStep  Satellites, run your app, and then any [frameworks](https://docs.lightstep.com/docs/python-auto-instrumentation#section-frameworks), [data stores](https://docs.lightstep.com/docs/python-auto-instrumentation#section-data-stores), and [libraries](https://docs.lightstep.com/docs/python-auto-instrumentation#section-libraries) included in your app will send data to LightStep as distributed traces.

## Requirements

- Python: 2.7, 3.4, 3.5, 3.6, 3.7

## Installing

```bash
pip install lighstep-ddtrace
```

## Getting Started

The following `app.py` makes a web request:

```python
#!/usr/bin/env python3
import requests

def get_url(url):
    response = requests.get(url)
    print(response)

if __name__ == "__main__":
    get_url("https://en.wikipedia.org/wiki/Duck")
```

Now let's run the application using `lightstep-ddtrace-run`

```bash
# export configuration options
export DD_TRACE_AGENT_URL=https://collector.lightstep.com:443
# replace <service_name> with your service's name
# replace <access_token> with your LightStep API token
export DD_TRACE_GLOBAL_TAGS="lightstep.service_name:<service_name>,lightstep.access_token:<access_token>"

# run the application
lighstep-ddtrace-run ./app.py
```

A trace from the application should be available in your [LightStep dashboard](https://app.lightstep.com/)

## Next Steps

Check out https://docs.lightstep.com/docs/python-auto-instrumentation for more information

## Support

Contact `support@lightstep.com` for additional questions and resources, or to be added to our community slack channel.

## Licensing

This is a fork of [dd-trace-py][dd-trace-py repo] and retains the original Datadog license and copyright. See the [license][license file] for more details.

[dd-trace-py repo]: https://github.com/DataDog/dd-trace-py
[license file]: https://github.com/lightstep/dd-trace-py/blob/master/LICENSE
