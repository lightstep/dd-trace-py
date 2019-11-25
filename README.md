# ls-trace-py

[![CircleCI](https://circleci.com/gh/lightstep/ls-trace-py/tree/master.svg?style=svg)](https://circleci.com/gh/lightstep/ls-trace-py/tree/master)
[![Pyversions](https://img.shields.io/pypi/pyversions/ls-trace.svg?style=flat)](https://pypi.org/project/ls-trace/)
[![PypiVersions](https://img.shields.io/pypi/v/ls-trace.svg)](https://pypi.org/project/ls-trace/)
[![OpenTracing Badge](https://img.shields.io/badge/OpenTracing-enabled-blue.svg)](http://pypi.datadoghq.com/trace/docs/installation_quickstart.html#opentracing)

Datadog has generously announced the [donation](https://www.datadoghq.com/blog/opentelemetry-instrumentation/) of their tracer libraries to the [OpenTelemety](https://opentelemetry.io/) project. Auto-instrumentation is a core feature of these libraries, making it possible to create and collect telemetry data without needing to change your code. LightStep wants you to be able to use these libraries now! We've forked the Datadog libraries into the LightStep repo as agents. You can install and use these agents to take advantage of auto-instrumentation without waiting for OpenTelemetry. Each LightStep agent is "pinned" to a Datadog release and is fully supported by LightStep’s Customer Success team.

Simply install the agent, configure it to communicate with LightStep Satellites, run your app, and then any [frameworks](https://docs.lightstep.com/docs/python-auto-instrumentation#section-frameworks), [data stores](https://docs.lightstep.com/docs/python-auto-instrumentation#section-data-stores), and [libraries](https://docs.lightstep.com/docs/python-auto-instrumentation#section-libraries) included in your app will send data to LightStep as distributed traces.

## Requirements

- Python: 2.7, 3.4, 3.5, 3.6, 3.7

## Installing

```bash
pip install ls-trace
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

Now let's run the application using `ls-trace-run`

```bash
# export configuration options
export DD_TRACE_AGENT_URL=https://collector.lightstep.com:443
# replace <service_name> with your service's name
# replace <access_token> with your LightStep access token
export DD_TRACE_GLOBAL_TAGS="lightstep.service_name:<service_name>,lightstep.access_token:<access_token>"

# run the application
chmod +x ./app.py
ls-trace-run ./app.py
```

A trace from the application should be available in your [LightStep dashboard](https://app.lightstep.com/)

## Additional Resources

Check out https://docs.lightstep.com/docs/python-auto-instrumentation for more information

## Versioning

ls-trace follows its own versioning scheme. The table below shows the corresponding dd-trace-py versions.

| ls-trace version | dd-trace-py version |
|------------------|---------------------|
| v0.1.0           | v0.31.0             |

## Support

Contact `support@lightstep.com` for additional questions and resources, or to be added to our community slack channel.

## Licensing

This is a fork of [dd-trace-py][dd-trace-py repo] and retains the original Datadog license and copyright. See the [license][license file] for more details.

[dd-trace-py repo]: https://github.com/DataDog/dd-trace-py
[license file]: https://github.com/lightstep/dd-trace-py/blob/master/LICENSE
