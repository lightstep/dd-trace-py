dist:
	mkdir -p dist
	rm -rf dist
	python setup.py sdist      # source distribution
	python setup.py bdist_wheel

publish: dist
	git push --tags
	twine upload dist/*

publish-test:
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

proto:
	protoc -I../lightstep/go/pkg/mod/github.com/gogo/protobuf@v1.2.1/protobuf/ --proto_path "$(PWD)/../googleapis:$(PWD)/../lightstep-tracer-common/" \
		--python_out="$(PWD)/ddtrace/vendor/lightstep" \
		collector.proto metrics.proto