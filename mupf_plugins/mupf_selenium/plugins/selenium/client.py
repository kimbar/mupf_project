import selenium

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from mupf.client import Client

class Selenium(Client):

    def __init__(self, app, client_id, driver=webdriver.Firefox):
        super().__init__(app, client_id)

        self.selenium: webdriver.remote.webdriver.WebDriver
        if type(driver) == type:
            self.selenium = driver()
        else:
            self.selenium = driver
        self.selenium.get(self.url)

    def close(self, *args, **kwargs):
        super().close(*args, **kwargs)
        self.selenium.close()

    def send_keys(self, text):
        actions = ActionChains(self.selenium)
        text = text.split('\n')
        first = True
        for part in text:
            if not first:
                actions.send_keys(Keys.RETURN)
            first = False
            if part:
                actions.send_keys(part)
        actions.perform()