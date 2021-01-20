import mupf
import time

mupf.log.enable('app.log', default_all_on=True)
print(mupf.F.feature_list)

with mupf.App(
        host='127.0.0.1',
        features = (
            - mupf.F.test_feature,
            - mupf.F.friendly_obj_names,    # This is not working - ReferenceError: id is not defined [static/core-esc.js:64:55]
            + mupf.F.verbose_macros,
        )
    ) as app:

    app.register_route('main.css', file='main.css')
    app.register_route('app.js', file='app.js')
    # app.register_route('jquery.js', file='jquery-3.4.1.min.js')

    client = app.summon_client()

    # client.install_javascript(src='jquery.js').result
    client.install_commands(src='app.js')
    client.command.install_css().wait

    # time.sleep(20)

    #client.command('*setfrn*').run(PseudoGhost(docid[1]), 'documento')

    cprint = client.command.print.run
    cinput = client.command.input

    cprint('Calculation of circle area v.1.0')

    h = client.window.document.body.innerHTML
    print(repr(h))
    client.window.mupf.test = client.window.document.body.innerHTML

    print(isinstance(client.window.document, str))

    r = float(cinput("Give me the radius: ").result)
    cprint(f'Circle area for r = {r} is equal to A = {3.141592653589793*r*r}')
    cprint('Thank you for your cooperation', color='red')

    client.command.sleep(1).wait
    # FIXED: without this `wait` there was some serious error, because server quited earlier than websocket coroutine
