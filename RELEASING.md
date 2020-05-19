# Releasing

Once all the changes for a release have been merged to master, ensure the following:

- [ ] version has been updated in `ddtrace/__init__.py` 
- [ ] tests are passing
- [ ] user facing documentation has been updated

# Publishing

Publishing to [pypi](https://pypi.org/project/ls-trace/) is automated via GitHub actions. Once a tag is pushed to the repo, a new GitHub Release is created and package is published  via the actions defined here: https://github.com/lightstep/ls-trace-py/blob/master/.github/workflows/createrelease.yml

```
$ git clone git@github.com:lightstep/ls-trace-py && cd ls-trace-py

# ensure the version matches the version beind released
$ cat ddtrace/__init__.py | grep version
__version__ = '0.1.0'

$ git tag v0.1.0 && git push origin v0.1.0
```
