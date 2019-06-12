mupf.hk.ccall = function(f, pyld) {
    pyld = mupf.esc.decode(pyld)
    return f.call(window, pyld.args, pyld.kwargs)  // this line is a bootstrap version of `ccall`
}

mupf.hk.presend = function(msg, res, cmd) {
    if (!cmd.noautoesc){
        res = mupf.esc.encode(res)
        msg[3].result = res
        msg[3].esc = 1
    }
    return [msg, res, cmd]
}
