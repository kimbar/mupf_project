import mupf
import time
import hashlib

def callback_function(event):
    global client
    print(event.target.textContent)
    # return hashlib.sha256(arg.encode('utf-8')).hexdigest()

with mupf.App() as app:
    client = app.summon_client()
    app.register_route('callback.js', file='callback.js')
    client.install_javascript(src='callback.js').wait

    client.window.button.onclick = callback_function

    while client:
        client.run_one_callback_blocking()
        time.sleep(0.01)
