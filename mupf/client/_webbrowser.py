
import webbrowser
from . import Client

class WebBrowserClient(Client):
    """
    `Client` that utilizes the `webbrowser` module interface.
    """
    def __init__(self, app, client_id):
        super().__init__(app, client_id)
        webbrowser.open(self.url)