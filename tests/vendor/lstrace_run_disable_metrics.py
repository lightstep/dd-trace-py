from ddtrace import tracer

if __name__ == "__main__":
    assert tracer._runtime_worker is None
    print("Test success")
