import mupf
import time
import hashlib

def callback_function(arg):
    print('Py side side-effect, arg = {}'.format(repr(arg)))
    return hashlib.sha256(arg.encode('utf-8')).hexdigest()

with mupf.App() as app:
    client = app.summon_client()
    app.register_route('callback.js', file='callback.js')
    client.install_javascript(src='callback.js').wait

    client.window.testfunc = callback_function

    while client:
        time.sleep(0.1)
