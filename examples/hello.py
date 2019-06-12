import mupf
app = mupf.App()
client = app.summon_client()
client.window.document.body.innerHTML = "Hello, World!"
client.close()
