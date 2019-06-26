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

mupf.hk.fndcmd = (n) => {
    if (typeof(n)==="string")
        return mupf.cmd[n]
    else if (typeof(n)==="number")
    {
        return async function(...args) {
            let clbid = mupf.clb.newid()
            let p = new Promise((ok, no) => { mupf.clb.waiting[clbid] = ok })
            let msgrescmd = mupf.hk.presend([5, clbid, n, {args: args}], args, {})
            mupf.send(msgrescmd[0])
            return await p
        }
    }
}
