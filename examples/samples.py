# Samples of `CommandSet`

cmd = client.command

cmds = (
    cmd.print('haha').wait +
    cmd.print('blabla').wait +
    cmd.input('Podaj liczbę:')
    )
x = float(cmds.results[-1])
cmd.print(f"liczba podana: {x}").wait

flash = cmd.flash.notification

flash()

cmd.print('haha').wait

flash()


# ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓ IMPORTANT ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓


document = Proxy(cmd.get_mupf(client.window, 'document').result)
body = Proxy(cmd.get_mupf(document, 'body').result)

# the same as:

body = client.window.document.body




document = Proxy(cmd.get_mupf(client.window, 'document').result)
createElement = Proxy(cmd.get_mupf(document, 'createElement').result)
element = Proxy(cmd.call_mupf(createElement, 'span').result)
cmd.set_mupf(element, 'innerHTML', 'hello world!').wait

# the same as:

element = client.window.document.createElement('span')
element.innerHTML = 'hello world!'


# It would be nice if it would be possible to replay GUI use in selenium based
# on the logs (JSON) from mupf. Bugs in replay!


Image = Proxy(cmd.get_mupf(client.window, 'Image').result)
img = Proxy(cmd.new_mupf(Image, 'param').result)

# the same as:

img = new(client.window.Image, 'param')

def new(constructor, *args, **kwargs):
	return Proxy(constructor[Internal.client].command('new_mupf')(constructor, *args, **kwargs).result)




r = cinput('podaj r').name('r')
h = cinput('podaj h').name('h')

data = r and h

r = data['r'].result    # r = data.r.result
h = data['h'].result

# or:

r, h = (cinput('podaj r') and cinput('podaj h')).result.tuple



to , tamto, to2 = (
		cinput('podaj to').default(0) or
		cinput('lub tamto').default(15) or
		cinput('ewentualnie to').default(100)
	).result.tuple
