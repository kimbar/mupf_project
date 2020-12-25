import os
import sys

def make_load_tests(init_file):
    """ Makes a `load_tests` function for `unittest`

    Unit tests are separated into (`venv`) environments with different
    installations. Each test suite for an environment is hold in respective
    directory of `/tests` directory. The environments are made with `nox`,
    however the discovery of tests should be restricted only for appropriate
    environment. To achieve this the `__init__.py` file of each tests suite
    should consist of:

    ```
    from mupftestsvenvhelper import make_load_tests
    load_tests = make_load_tests(__file__)
    ```

    This makes a `load_tests` function, which fails to discover any tests if
    the environment does not match the test suite. Any subsequent packages
    inside of the test suites for environment should have empty `__init__.py`
    files.
    """

    def load_tests(loader, standard_tests, pattern):
        nonlocal init_file    # The `__init__.py` file of the test suite
        test_suite_dir = os.path.dirname(init_file)

        if os.path.basename(sys.prefix) != os.path.basename(test_suite_dir):
            return standard_tests

        package_tests = loader.discover(start_dir=test_suite_dir, pattern=pattern)
        standard_tests.addTests(package_tests)
        return standard_tests

    return load_tests