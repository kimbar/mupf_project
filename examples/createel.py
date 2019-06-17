import mupf
app = mupf.App(
    features=(
        + mupf.F.disable_garbage_collection,
    )
)
client = app.summon_client()

document = client.window.document
span = document.createElement('span')
span.innerHTML = "SPAM!!! span"
document.body.appendChild(span)

client.close()
