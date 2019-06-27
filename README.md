# mupf
Low-level browser DOM manipulation from Python

Mupf aims at tapping into great GUI potential of modern browsers for Python. It
is **not a web app framework**. It connects the Python side through a WebSocket
to the JavaScript of a local machine browser. Virtually any manipulation of DOM
is possible from that point without writing any JavaScript (however,
transferring the logic from Py to JS is encouraged as an app matures).
Potentially any web GUI framework (or none) can be used on the front-end side.

It is as easy as:

```Python
import mupf

with mupf.App().open_with_client() as client:
    client.window.document.body.innerHTML = "Hello, World!"
```

![Hello world example result](./docs/hello_example.png)

But what about some interactivity?

```Python
import mupf
import hashlib

# Event handler
def button_click(event):
    """ Calculate SHA256 of the input and print it below
    """
    global input_, bodyAppendChild, createElement
    value = input_.value
    hash_ = hashlib.sha256(value.encode('utf-8')).hexdigest()
    span = createElement('span')
    span.innerHTML = f"SHA256({repr(value)}) = {hash_}"
    bodyAppendChild(span)
    bodyAppendChild(createElement('br'))

with mupf.App() as app:
    client = app.summon_client()

    # Useful functions
    createElement = client.window.document.createElement
    bodyAppendChild = client.window.document.body.appendChild

    # Creating the GUI
    button = createElement('button')
    input_ = createElement('input')
    bodyAppendChild(input_)
    bodyAppendChild(button)
    bodyAppendChild(createElement('br'))
    button.textContent = 'SHA256'
    # Attaching an event handler (Python-side function!)
    button.onclick = button_click

    # Process events
    while client:
        client.run_one_callback_blocking()
```

![Interactive example result](./docs/sha256_example.png)

A little verbose? Sure, but that's because it's all done in pure Python. Not
just these two lines that do the actual work, but also all the GUI building,
event handling etc. This allows for crude prototyping of applications in single
language, and to split them later among "model" (Python) and "view" (Java
Script) parts as they mature. You can decide then, after they prove themselves
to work, what to keep on the "model" side and what to move to the Java Script
side for performance and clarity. You can also use any frontend framework
(since mupf is as low-level as it gets) from the get-go.
