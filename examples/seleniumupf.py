import mupf
import time

app = mupf.App()
app.open()
app.register_route('main.css', file='main.css')
app.register_route('app.js', file='app.js')

client = app.summon_client(frontend=mupf.client.Selenium)

client.install_commands(src='app.js')
client.command.install_css().wait

cprint = client.command.print.run
cinput = client.command.input

cprint('Calculation of circle area v.1.0')
r = cinput("Give me the radius: ")

time.sleep(1.0)
client.send_keys("120\n")
r = float(r.result)

cprint(f'Circle area for r = {r} is equal to A = {3.141592653589793*r*r}')
cprint('Thank you for your cooperation', color='red')

client.command.sleep(2)

client.close()
app.close()
