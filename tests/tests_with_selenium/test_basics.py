import nose
from nose.tools import istest, nottest, timed

import mupf
import time

@istest
def hello_world():
    app = mupf.App()
    time.sleep(2)
    if not app._event_loop.is_running():
        raise RuntimeError("No eventloop")
    client = app.summon_client(frontend=mupf.client.Selenium)
    client.window.document.body.innerHTML = "Hello, World!"
    client.close()
    app.close()
