
mupf.cmd.print = function(args, kwargs){ 
    let h = args.join(kwargs.sep || " ")
    let sp = document.createElement('span')
    if (kwargs.color !== undefined) sp.setAttribute('style', 'color:'+kwargs.color)
    sp.innerHTML = h + (kwargs.end || "<br>")
    document.body.appendChild(sp)
}

mupf.cmd.install_css = async function(args, kwargs){
    let lk = document.createElement('link')
    await new Promise((ok, no) => {
        lk.addEventListener('load', () => { ok() })
        lk.addEventListener('error', (e) => { no(Error('MupfError\nUnable to load script')) })
        lk.setAttribute('rel', 'stylesheet')
        lk.setAttribute('href', 'main.css')
        document.head.appendChild(lk)
    })
}

mupf.cmd.input = async function(args, kwargs){
    let prompt = ">>> "
    if (args.length > 0) prompt = args[0]
    let sp = document.createElement('span')
    sp.appendChild(document.createTextNode(prompt))
    let inp = sp.appendChild(document.createElement('input'))
    sp.appendChild(document.createElement("br"))
    document.body.appendChild(sp)
    inp.focus()
    let result = await new Promise((ok, no) => {
        inp.onkeyup = (e) => { if (e.keyCode===13) ok(e.target.value) }
    })
    sp.replaceChild(document.createTextNode(result), inp)
    return result
}

mupf.cmd.sleep = async function(args, kwargs){
    let t = args[0]
    await new Promise((ok, no) => {
        setTimeout(ok, t*1000.0)
    })
    return t
}
