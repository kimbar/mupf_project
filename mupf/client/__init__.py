from ._base import Client
from ._webbrowser import WebBrowser

from .._plugins_manager import inject_by_class

inject_by_class(globals(), Client)
