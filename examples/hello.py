import logging
logging.basicConfig(filename='output.log', filemode='w', level=logging.INFO)

import mupf

with mupf.App().open_with_client() as client:
    client.window.document.body.innerHTML = "Hello, World!"
