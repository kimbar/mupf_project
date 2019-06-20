import mupf
app = mupf.App(
    features=(
        - mupf.F.garbage_collection,
    )
)
client = app.summon_client()
client.install_javascript("""
    mupf.hk.getmsg = (ev) => {
        console.log(ev.data)
        return JSON.parse(ev.data)
    }
""", remove=True)

document = client.window.document
span = document.createElement('span')
span.innerHTML = "SPAM!!! span"
document.body.appendChild(span)

client.close()
