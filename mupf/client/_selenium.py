import mupf

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from ..client import Client

class Selenium(Client):
    
    def __init__(self, app, client_id, driver=webdriver.Firefox):
        super().__init__(app, client_id)
        if type(driver) == type:
            self.driver = driver()
        else:
            self.driver = driver
        self.driver.get(self.url)

    def close(self, *args, **kwargs):
        super().close(*args, **kwargs)
        self.driver.close()

    def send_keys(self, text):
        actions = ActionChains(self.driver)
        text = text.split('\n')
        first = True
        for part in text:
            if not first:
                actions.send_keys(Keys.RETURN)
            first = False
            if part:
                actions.send_keys(part)
        actions.perform()