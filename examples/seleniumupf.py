
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import mupf
import time

class SeleniumClient(mupf.Client):
    
    def __init__(self, app, client_id):
        super().__init__(app, client_id)
        self.driver = webdriver.Firefox()
        self.driver.get(self.url)

    def close(self):
        super().close()
        self.driver.close()


app = mupf.App()
app.register_route('main.css', file='main.css')
app.register_route('app.js', file='app.js')

client = app.summon_client(frontend=SeleniumClient)

client.install_javascript(src='mupf/core').result
client.install_commands(src='app.js')
client.command.install_css().wait

docid = client.command('*get*')(["~",["~@", None],{}], 'document').result
bodyid = client.command('*get*')(["~",["~@", docid[1]],{}], 'body').result

cprint = client.command.print.run
cinput = client.command.input

cprint('Calculation of circle area v.1.0')
r = cinput("Give me the radius: ")

time.sleep(1.0)
actions = ActionChains(client.driver)
actions.send_keys("120")
actions.send_keys(Keys.RETURN)
actions.perform()

r = float(r.result)

cprint(f'Circle area for r = {r} is equal to A = {3.141592653589793*r*r}')
cprint('Thank you for your cooperation', color='red')

client.command.sleep(2)

client.close()
app.close()
