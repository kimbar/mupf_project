from ._base import Client
from ._webbrowser import WebBrowser

from .._plugins_manager import inject, iterate_by_supclass
inject(__name__, globals(), iterate_by_supclass, class_=Client)
del iterate_by_supclass, inject
