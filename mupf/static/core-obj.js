window.mupf.obj = {
    // # public
    // #
    getid: function (obj) {
        let id = 0
        for (id in this._byid)
        // #if friendly_obj_names
            if (Object.is(this._byid[id][0], obj)) return Number(id)
        // #else
            if (Object.is(this._byid[id], obj)) return Number(id)
        // #endif
        id = this._idcounter
        this._idcounter++
    // #if friendly_obj_names
        this._byid[id] = [obj, {}]
    // #else
        this._byid[id] = obj
    // #endif
        return id
    },
    byid: function (id) { return this._byid[id] },
    del: function (id) {
        // #if garbage_collection
        delete this._byid[id]
        // #endif
    },
    // # private
    // #
// #if friendly_obj_names
    _byid: { 0: [window, {frn: "window"}] },
// #else
    _byid: { 0: window },
// #endif
    _idcounter: 1
}
