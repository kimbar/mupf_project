import nox

@nox.session(venv_backend='venv')
def vanilla(s):
    common(s)
    # and here run all tests!

@nox.session(venv_backend='venv')
def selenium(s):
    common(s)
    # install selenium plugin here
    # and here run all tests!

def common(s):
    s.log('Installing `mupf-test-venv-helper`')
    s.install('./venv-helper/.')
    s.log('Installing `mupf` in editable mode')
    s.install('-e', '../.')
