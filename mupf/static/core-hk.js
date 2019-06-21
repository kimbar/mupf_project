mupf.hk.ccall = function(f, pyld) {
    pyld = mupf.esc.decode(pyld)
    return f.call(window, pyld.args, pyld.kwargs)  // this line is a bootstrap version of `ccall`
}

mupf.hk.presend = function(msg, res, cmd) {
    let enhb = {c: 0, noautoesc: cmd.noautoesc}
    msg[3].result = mupf.esc.encode(res, enhb)
    if (enhb.c > 0){
        delete enhb.noautoesc
        msg[3] = ["~", msg[3], enhb]
    }
    return [msg, res, cmd]
}
