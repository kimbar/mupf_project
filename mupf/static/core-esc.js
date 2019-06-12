mupf.esc = {
    "~": function(x, opt){ this._enhb.push(opt); let r =  this.decode(x); this._enhb.pop(); return r },
    "~~": function(x){ for(let i=0; i<x.length; i++) x[i] =  this.decode(x[i]); return x },
    "~-": (x) => x,
// #if friendly_obj_names
    "~@": (x) => mupf.obj.byid(mupf.esc.decode(x))[0],
// #else
    "~@": (x) => mupf.obj.byid(mupf.esc.decode(x)),
// #endif
    "~$": function(ccid, name, a){ // This is almost exactly the same as `mupf.recv()`
        let cmd = mupf.hk.fndcmd(name)
        if (cmd===undefined) throw new mupf.MupfError('CommandUnknownError', name)
        let result = mupf.hk.ccall(cmd, a)
        if (result instanceof Promise) result = result   // FIXME - commands returning a `Promise` ashould be forbidden here or everything should be rebuild
        return result
    },
    "~S": (x) => special[ mupf.esc.decode(x)],
    special: {'undefined': undefined, 'NaN': NaN, 'Infinity': Infinity, '-Infinity': -Infinity},
    _enhb: [],
    decode: function(x) {
        if (Array.isArray(x)) {
            if ((x.length > 1) && (typeof(x[0])==="string") && (x[0].substr(0,1)==="~") && (x[0]==="~" || mupf.esc._enhb.length > 0)) {
                return mupf.esc[x[0]].apply(mupf.esc, x.slice(1))
            }
            for (let i=0; i<x.length; i++) x[i] = mupf.esc.decode(x[i])
            return x
        }
        else if (x===null) return x
        else if (typeof(x) === 'object') {
            for (let k of Object.keys(x)) x[k] = mupf.esc.decode(x[k])
            return x
        }
        return x
    },
    encode: function(x) {
        if (x === null) return x
        if (typeof(x) === 'object' || typeof(x) === 'function'){
            let id = mupf.obj.getid(x)
        // #if friendly_obj_names
            return ["~@", id, mupf.obj.byid(id)[1].frn]
        // #else
            return ["~@", id]
        // #endif
        }
        if (typeof(x) === 'undefined') return ["~S", "undefined"]
        return x
    }
}
