"""
This module should be installed in testing environments.

It should not be installed in developement environment nor in an environment
where the mupf is used. Normally the `/tests/noxfile.py` installs it.

 * `make_load_tests()`
   Makes a `load_tests` function for `unittest`
 * `repair_plugins()`
   Repairs the `mupf.__path__` to find plugins during developement
"""

import os
import sys

def make_load_tests(init_file):
    """ Makes a `load_tests` function for `unittest`

    Unit tests are separated into (`venv`) environments with different
    installations. Each test suite for an environment is hold in respective
    directory of `/tests` directory. The environments are made with `nox`,
    however the discovery of tests should be restricted only to appropriate
    environment. To achieve this, the `__init__.py` file of each test suite
    should consist of:

    ```
    from mupftestsvenvhelper import make_load_tests
    load_tests = make_load_tests(__file__)
    ```

    This makes a `load_tests` function, which is used by `unittests`. It fails
    to discover any tests if the environment does not match the test suite. Any
    subsequent packages inside of the top test suite for environment should
    have empty `__init__.py` files as usual.
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

def repair_plugins(mupf_package_path):
    """ Repairs the `mupf.__path__` to find plugins during developement

    The `mupf.plugins` is a namespace package. If all is installed normally
    (not for developement) all is all right. The plugins are placed in
    `site-packages/mupf/plugins` and are discoverd as they should.

    The problem arises when `mupf` and plugins are installed with
    `pip -e install .`

    In this case, the "parent path" (as said in PEP 420) must be altered
    aproprietly. However, the "parent path" is not `sys.path` (which is
    modified from `easy-install.pth` file as it should), but the
    `mupf.__path__` (which holds only the path for `mupf` itself). It is
    possible that there is another mechanism to alter this path, but I don't
    know it.

    This function is ivoked in `mupf/__init__.py`. It should not be used
    elswhere.

    THIS IS A HACK

    """
    try:
        fp = open(os.path.join(os.path.dirname(__file__), 'easy-install.pth'), 'r')
    except IOError:
        print('repair_plugins: cannot open the `easy-install.pth` file')
    else:
        for line in fp:
            if '\\mupf_plugins\\' in line:
                mupf_package_path.append(line.strip('\n'))
        fp.close()