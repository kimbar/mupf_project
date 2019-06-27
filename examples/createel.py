import mupf
app = mupf.App(
    features=(
        - mupf.F.garbage_collection,
    )
)
app.open()

client = app.summon_client()
client.install_javascript("""
    mupf.hk.getmsg = (ev) => {
        console.log(ev.data)
        return JSON.parse(ev.data)
    }
    mupf.cmd.echo = function(args, kwargs){
        return args
    }
    mupf.cmd.echo.noautoesc = true
""", remove=True)

document = client.window.document
span = document.createElement('span')
span.innerHTML = "SPAM!!! span"
document.body.appendChild(span)

print(client.command.echo("nice", "args").result)
print(client.command.echo("~~~~", "nasty", "set", "of", "args").result)

print(span.innerHTML)

app.close()
