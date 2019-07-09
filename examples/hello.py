import mupf

mupf.log.enable('output.log', level=mupf.log.logging.INFO, filters=('+ ***/create_send_task', '+ ***/Client.decode_json'))

with mupf.App().open_with_client() as client:
    client.window.document.body.innerHTML = "Hello, World!"
