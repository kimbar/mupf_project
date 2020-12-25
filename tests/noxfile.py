import nox

@nox.session(venv_backend='venv')
def vanilla_env(s):
    common(s)
    # and here run all tests!

@nox.session(venv_backend='venv')
def selenium_env(s):
    common(s, editable=True)
    s.install('-e', '../mupf_plugins/mupf_selenium/.')
    # and here run all tests!

def common(s, editable=True):
    s.log('Installing `mupf-test-venv-helper`')
    s.install('./venv-helper/.')
    s.log('Installing `mupf` in editable mode')
    if editable:
        s.install('-e', '../.')
    else:
        s.install('../.')
