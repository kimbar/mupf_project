import mupf
app = mupf.App().open()
client = app.summon_client()
client.window.document.body.innerHTML = "Hello, World!"
app.close()
