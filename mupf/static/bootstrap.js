(() => {    // This is unnamed function to prevent scope pollution
"use strict"
// Main script run after the documnet is loaded
function main() {

    // Main library object (skeleton)
    window.mupf = {cmd: {}, hk:{}, pending: 0, fts: {}}

    // sends a data packet to the Python side
    mupf.send = function(msg) {
        mupf.ws.send(JSON.stringify(msg))
        if (msg[0]==1){    // mode=res
            mupf.pending--
            if (mupf.last_resolve && mupf.pending == 1)
                mupf.last_resolve()
        }
    }

    class MupfError extends Error {
        constructor(mn, ...params){
            super(...params)
            this.mupfname = mn
    }}

    mupf.MupfError = MupfError

    mupf.hk.fndcmd = (n) => mupf.cmd[n]
    mupf.hk.ccall = (f, pyld) => f.call(window, pyld.args, pyld.kwargs)
    mupf.hk.getmsg = (ev) => JSON.parse(ev.data)
    // chainable:
    mupf.hk.presend = (msg, cmd) => [msg, cmd]
    mupf.hk.postntf = (msg, cmd) => [msg, cmd]  // TODO: temporarily removed - recreate
    mupf.hk.postcmd = (msg, cmd) => [msg, cmd]
    mupf.hk.preclose = () => undefined
    
    mupf.res = function(msg, result, cmd) {
        if (result === undefined) result = null
        let msgcmd = mupf.hk.presend([1,msg[1],0,{result:result}], cmd)
        mupf.send(msgcmd[0])
        mupf.hk.postcmd(msgcmd[0], msgcmd[1]) // this line tries to execute when the cmd does not exist
    }

    mupf.recv = function(msg){
        let mode = msg[0]
        if (mode === 0){
            mupf.pending++
            let result = null
            let cmd = mupf.hk.fndcmd(msg[2])
            try {
                if (cmd===undefined) throw new MupfError('CommandUnknownError', msg[2])
                result = mupf.hk.ccall(cmd, msg[3])
                if (result instanceof Promise)
                    result.then((r) => mupf.res(msg, r, cmd))
                else
                    mupf.res(msg,result,cmd)
            } catch (err) {
                let errname = err.constructor.name
                if (errname=='MupfError') errname = err.mupfname
                mupf.send([1, msg[1], 1, {result:[errname, err.message, err.fileName, err.lineNumber, err.columnNumber]}])   // this is not good, becouse "Error/nMupfError/nUnable to load script" will be send
                return
            }
            return

        } else if (mode === 2){
            let cmd = mupf.hk.fndcmd(msg[2])
            if (cmd === undefined) return  // maybe postntf should be called when there is no cmd?
            mupf.hk.ccall(cmd, msg[3])
            // here `postntf`
            return

        } else if (mode === 6){
            mupf.clb.waiting[msg[1]](msg[3])
        } else {
            // unknown mode
        }
    }


    // command run at the very beginning, setups `window.mupf`
    mupf.cmd['*first*'] = async function(args, kwargs){
        document.head.removeChild(document.getElementById('mupf-bootstrap'))
        Object.assign(window.mupf.fts, kwargs)
        mupf.cid = window.location.hash.substring(1)                       // client id
        mupf.ws = await new Promise((ok, no) => {                          // web socket
            let ws = new WebSocket("ws://"+window.location.host+"/mupf/ws")
            ws.onopen = () => { ok(ws) }
            ws.onerror = (e) => { no(e) }   // co z tym errorerm?
            ws.onmessage = (ev) => {mupf.recv(mupf.hk.getmsg(ev)) }
            ws.onclose = (e) => {}
        })
        window.addEventListener('unload',async function(e){await mupf.send([7,0,'*close*',{result:null}])}) // TODO: this send as ntf
        return {cid: mupf.cid, ua: navigator.userAgent}
    }

    mupf.cmd['*last*'] = async function(args, kwargs){
        // Not so fast, what if commands are still hanging?
        if (mupf.pending > 1) await new Promise((ok, no) => {mupf.last_resolve = ok})
        mupf.hk.preclose()
        window.mupf.ws.close(1000, "*last*")
        // This command returns `null` through a closed websocket. Is this a problem?
    }

    //*install* a script, any script in particular, more commands may be installed this way
    mupf.cmd['*install*'] = async function(args, kwargs){
        let sc = document.createElement('script')
        await new Promise((ok, no) => {
            if (args.length == 1) sc.innerHTML = args[0]
            document.head.appendChild(sc)
            if (kwargs.hasOwnProperty('src')) {
                sc.addEventListener('load', () => {ok()})
                sc.addEventListener('error', (e) => {no(new mupf.MupfError('MupfError','Unable to load script src="'+e.target.src+'"'))})
                sc.src = kwargs['src']
            }
            else ok()
        })
        if (kwargs.remove) document.head.removeChild(sc)
    }

    mupf.cmd['*features*'] = function(){return mupf.fts}

    // The `*first*` command is a special case. In all respects it is a normal command except for
    // that it cannot be sent from Python, because when it is called there is no websocket present
    // yet. This is due to the fact, that `__first__` creates this websocket. On the Python side
    // the sending of this command is supressed, but somwhere it must be called eventualy. This is
    // here. No other command is ever called like that, only `__first__`.

    mupf.recv([0,0,"*first*",{args:[],kwargs:{
        _user_feature: (2+2 == 4)
    }}])

    // The `*last*` command is also a special case. This command is symetrical to `*first*` in
    // being special -- it is not in a notification mode, but it cannot send its result
    // because it closes the websocket. But the 
    
}   // end of `main()`

// This part is taken from jQuery - it ensures that `main()` is run exactly once after the document
// is fully loaded
function run_main() {
    document.removeEventListener("DOMContentLoaded", run_main)
    window.removeEventListener("load", run_main)
    main()
}

if (document.readyState === "complete" || (document.readyState !== "loading" && !document.documentElement.doScroll))
    window.setTimeout(main)
else {
    document.addEventListener("DOMContentLoaded", run_main)
    window.addEventListener("load", run_main)
}

})()   // run the anonymous function
