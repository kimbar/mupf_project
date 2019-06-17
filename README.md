# mupf_project
Low-level browser DOM manipulation from Python

Mupf aims at tapping into great GUI potential of modern browsers for Python. It is **not** a webapp framework.
It connects the Python side through a websocket to the JavaScript of a local machine browser. Virtually any
DOM manipulation of DOM is possible from that point without writeing any JavaScript (however, transfering
the logic from Python to JS is encouraged as an app matures). Potentially any web GUI framework can be used
on the frontend side.

It is as easy as:
```Python
import mupf
app = mupf.App()
client = app.summon_client()
client.window.document.body.innerHTML = "Hello, World!"
client.close()
```
