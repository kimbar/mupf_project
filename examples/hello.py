import logging

logging.basicConfig(level=logging.INFO)
hand = logging.FileHandler(filename='output.log', mode='w', encoding='utf-8')
hand.setFormatter(logging.Formatter(fmt='%(asctime)s %(message)s'))
logging.getLogger('mupf').addHandler(hand)

import mupf

with mupf.App().open_with_client() as client:
    client.window.document.body.innerHTML = "Hello, World!"
