import mupf

mupf.log.enable('output.log', level=mupf.log.logging.DEBUG)

with mupf.App().open_with_client() as client:
    client.window.document.body.innerHTML = "Hello, World!"
