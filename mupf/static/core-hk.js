mupf.hk.ccall = function(f, pyld) {
    pyld = mupf.esc.decode(pyld)
    return f.call(window, pyld.args, pyld.kwargs)  // this line is a bootstrap version of `ccall`
}

mupf.hk.presend = function(msg, cmd) {
    let enhb = {c: 0, noautoesc: cmd.noautoesc}
    if (msg[0] == 1)
        msg[3].result = mupf.esc.encode(msg[3].result, enhb)
    else if (msg[0] == 5) {
        for (let i=0; i<msg[3].args.length; i++)
            msg[3].args[i] = mupf.esc.encode(msg[3].args[i], enhb)
    }

    if (enhb.c > 0){
        delete enhb.noautoesc
        msg[3] = ["~", msg[3], enhb]
    }
    return [msg, cmd]
}

mupf.hk.fndcmd = (n) => {
    if (typeof(n)==="string")
        return mupf.cmd[n]
    else if (typeof(n)==="number")
    {
        if (mupf.clb._byid[n]===undefined){
            mupf.clb._byid[n] = async function(...args) {
                let clbid = mupf.clb.newid()
                let p = new Promise((ok, no) => { mupf.clb.waiting[clbid] = ok })
                let msgrescmd = mupf.hk.presend([5, clbid, n, {args: args}], mupf.clb._byid[n])
                mupf.send(msgrescmd[0])
                return await p
            }
        }
        return mupf.clb._byid[n]
    }
}
