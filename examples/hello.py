import mupf

with mupf.App().open_with_client() as client:
    client.window.document.body.innerHTML = "Hello, World!"
