Object.keys(mupf.cmd).forEach((c) => mupf.cmd[c].noautoesc=true)

mupf.ObjWCntx = function(obj, cntx){this.obj=obj; this.cntx=cntx}

mupf.cmd['*get*'] = function (args, kwargs) {
    let x = args[0][args[1]]
    if (x === undefined) throw new mupf.MupfError('DOMAttributeError', 'object has no attribute \'' + args[1] + '\'')
    return new mupf.ObjWCntx(x, args[0])
}

mupf.cmd['*set*'] = function(args, kwargs) {
    args[0][args[1]] = args[2]
}

mupf.cmd['*call*'] = function(args, kwargs) {
    let f = mupf.obj.byid(kwargs.objid)
    return f.apply(kwargs.cntx, args)
}

mupf.cmd['*gc*'] = function(args, kwargs) { mupf.obj.del(args[0]) }
mupf.cmd['*gc*'] .noautoesc = true

// #if friendly_obj_names
mupf.cmd['*setfrn*'] = function(args, kwargs) { mupf.obj.byid(mupf.obj.getid(args[0]))[1].frn = args[1] }
mupf.cmd['*setfrn*'].noautoesc = true
// #endif

mupf.cmd['*getcmds*'] = function(){return Object.keys(mupf.cmd)}
mupf.cmd['*getcmds*'].noautoesc = true
