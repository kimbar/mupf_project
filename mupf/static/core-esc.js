mupf.esc = {
    "~": function(x, opt){
        this._enhb.push(opt)
        let r =  this.decode(x)
        opt = this._enhb.pop()
        if (opt.proms !== undefined){
            console.log(opt.proms)
        }
        return r
    },
    "~~": function(x){ for(let i=0; i<x.length; i++) x[i] =  this.decode(x[i]); return x },
    "~-": (x) => x,
// #if friendly_obj_names
    "~@": (x) => mupf.obj.byid(mupf.esc.decode(x))[0],
// #else
    "~@": (x) => mupf.obj.byid(mupf.esc.decode(x)),
// #endif
    "~$": function(ccid, name, argskwargs){ // This is almost exactly the same as `mupf.recv()`
        let cmd = mupf.hk.fndcmd(name)
        if (cmd===undefined) throw new mupf.MupfError('CommandUnknownError', name)
        if (argskwargs === undefined)
            return cmd
        else
            throw new mupf.MupfError('NotImplementedError', "compound commands")
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
    encode: function(x, enhb) {
        if (enhb.noautoesc){
            if (Array.isArray(x) && (x.length > 1) && (typeof(x[0])==="string") && (x[0].substr(0,1)==="~")) {
                enhb.c += 1
                return ["~-", x]    // This is simple, but `noautoesc=true` commands cannot have complex objects in result
            }
            else
                return x
        }
        if (x === null) return x
        if (typeof(x) === 'object' || typeof(x) === 'function'){
            let id, thisid
            if (x.constructor === mupf.esc.Any){
                id = mupf.obj.getid(x.obj)
                if (x.obj.apply === undefined)
                    thisid = null
                else
                    thisid = mupf.obj.getid(x.this_)
            } else {
                id = mupf.obj.getid(x)
                thisid = null
            }
            enhb.c += 1
        // #if friendly_obj_names
            return ["~@", id, thisid, mupf.obj.byid(id)[1].frn]
        // #else
            return ["~@", id, thisid]
        // #endif
        }
        if (typeof(x) === 'undefined') {
            enhb.c += 1
            return ["~S", "undefined"]
        }
        return x
    },
    Any: class {
        constructor(obj, this_) {
            this.obj = obj
            this.this_ = this_
        }
    }
}
