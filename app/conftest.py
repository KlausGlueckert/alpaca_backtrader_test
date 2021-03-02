def pytest_addoption(parser):
    parser.addoption("--log", action="store", default="default name")