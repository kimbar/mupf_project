.. mupf documentation master file, created by
   sphinx-quickstart on Tue Jan  5 14:39:17 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

mupf
====

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Low-level browser DOM manipulation from Python

Mupf aims at tapping into great GUI potential of modern browsers for Python. It is not a web app framework. It connects
the Python side through a WebSocket to the JavaScript of a local machine browser. Virtually any manipulation of DOM is
possible from that point without writing any JavaScript (however, transferring the logic from Py to JS is encouraged as
an app matures). Potentially any web GUI framework (or none) can be used on the front-end side.

.. autoclass:: mupf._app.App
   :members:
   :private-members:
   :special-members:

.. autoclass:: mupf.client.Client
   :members:
   :private-members:
   :special-members:

.. autoclass:: mupf._remote.RemoteObj
   :members:
   :private-members:
   :special-members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
