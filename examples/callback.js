var button = document.createElement('button')
var input = document.createElement('input')
document.body.appendChild(input)
document.body.appendChild(button)
document.body.appendChild(document.createElement('br'))
button.textContent = 'SHA256'
button.onclick = async function(ev){
    mupf.cmd.print([await window.testfunc(window.input.value)],{})
}

mupf.cmd.print = function(args, kwargs){ 
    let h = args.join(kwargs.sep || " ")
    let sp = document.createElement('span')
    if (kwargs.color !== undefined) sp.setAttribute('style', 'color:'+kwargs.color)
    sp.innerHTML = h + (kwargs.end || "<br>")
    document.body.appendChild(sp)
}