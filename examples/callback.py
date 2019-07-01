import mupf
import hashlib

mupf.enable_logging('callback.log')

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
