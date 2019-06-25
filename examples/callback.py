import mupf
import time

class FakeCallback:
    def __init__(self, number):
        self.number = number
    def json_esc(self):
        return "$", None, self.number

with mupf.App() as app:
    client = app.summon_client()
    app.register_route('callback.js', file='callback.js')
    client.install_javascript(src='callback.js').wait

    client.window.testfunc = FakeCallback(384)

    while True:
        time.sleep(0.5)
        if not client._healthy_connection:
            break
