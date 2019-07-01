import mupf
import mupf._logging as log

print(log._loggables)

# mupf.enable_logging('output.log')

with mupf.App().open_with_client() as client:
    client.window.document.body.innerHTML = "Hello, World!"

print(log._loggables)
