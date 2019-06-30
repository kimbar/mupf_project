
import webbrowser
from . import Client

class WebBrowser(Client):
    """
    `Client` that utilizes the `webbrowser` module interface.
    """
    def __init__(self, app, client_id):
        super().__init__(app, client_id)
        webbrowser.open(self.url)

    def __repr__(self):
        return "<WebBrowser>"