
mupf.clb = {
    newid: function() { return this._idcounter++ },
    waiting: {},
    _idcounter: 0
}

mupf.hk.fndcmd = (n) => {
    if (typeof(n)==="string")
        return mupf.cmd[n]
    else if (typeof(n)==="number")
    {
        return async function(arg){
            let clbid = mupf.clb.newid()
            let p = new Promise((ok, no) => {
                mupf.clb.waiting[clbid] = ok
            })
            mupf.send([5, clbid, n, arg])
            return await p
        }
    }
}
