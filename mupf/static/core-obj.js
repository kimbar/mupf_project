window.mupf.obj = {
    // # public
    // #
    getid: function (obj) {
        let id = 0
        for (id in this._byid)
        // #if friendly_obj_names
            if (Object.is(this._byid[id][0], obj)) return id
        // #else
            if (Object.is(this._byid[id], obj)) return id
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
        // #if ~disable_garbage_collection
        delete this._byid[id]
        // #endif
    },
    // # private
    // #
// #if friendly_obj_names
    _byid: { null: [window, {frn: "window"}] },
// #else
    _byid: { null: window },
// #endif
    _idcounter: 0
}
