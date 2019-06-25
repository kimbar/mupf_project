import nose
from nose.tools import istest, nottest, timed

import mupf
import time

@istest
def hello_world():
    print("######################## start #########################")
    app = mupf.App(port = 57111)
    time.sleep(2)
    if not app._event_loop or not app._event_loop.is_running():
        app.close()
        raise RuntimeError("No eventloop")
    client = app.summon_client(frontend=mupf.client.Selenium)
    client.window.document.body.innerHTML = "Hello, World!"
    client.close()
    app.close()
