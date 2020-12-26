import unittest
import os
import sys
from selenium import webdriver
import mupf
import time

class Import(unittest.TestCase):

    def setUp(self) -> None:
        print(self.shortDescription())
        os.chdir(os.path.dirname(__file__))
        self.t0 = time.time()

    def test_import(self):
        "selenium/basics: None -> Import the `Selenium` class from the plugin"
        import mupf.plugins
        from mupf.client import Selenium

        print('mupf.__path__ =', mupf.__path__)
        print('mupf.plugins.__path__ =', mupf.plugins.__path__)

    def test_geckodriver_firefox(self):
        "selenium/basics: None -> Run Firefox webdriver (geckodriver)"
        driver = webdriver.Firefox()
        driver.close()

    def test_hello_world(self):
        "selenium/basics: None -> Display 'Hello, World!' example"
        text = "Hello, World!"
        with mupf.App() as app:
            client = app.summon_client(frontend=mupf.client.Selenium)
            client.window.document.body.innerHTML = text

            body = client.selenium.find_element_by_tag_name('body')
            self.assertEqual(body.text, text)

    def tearDown(self) -> None:
        print(f'Test run time: {int((time.time()-self.t0)*1000)} ms')

# import socket
# from selenium import webdriver
# import time

# import mupf
# import mupf.exceptions



# @istest


# @istest
# def append_element():
#     """with_selenium/basics: None -> Create and append a <span>
#     """
#     with mupf.App() as app:
#         client = app.summon_client(frontend=mupf.client.Selenium)
#         createElement = client.window.document.createElement
#         bodyAppendChild = client.window.document.body.appendChild
#         bodyAppendChild(createElement('span'))

#         body = client.selenium.find_element_by_tag_name('body')
#         span = body.find_element_by_tag_name('span')
#         assert isinstance(span, webdriver.remote.webelement.WebElement)

# @istest
# def user_close():
#     """with_selenium/basics: None -> Userlike close of client waiting on a callback
#     """
#     def userlike_action(client):
#         client.selenium.quit()

#     with mupf.App() as app:
#         client = app.summon_client(frontend=mupf.client.Selenium)
#     try:
#         app.piggyback_call(userlike_action, client)
#         while client:
#             client.run_one_callback_blocking()
#     except mupf.exceptions.ClientClosedUnexpectedly:
#         pass

# @istest
# def trigger_event():
#     """with_selenium/basics: None -> Userlike triggering of a click event
#     """
#     sentinel = False
#     def event_handler(event):
#         nonlocal sentinel
#         sentinel = True

#     def userlike_action(client):
#         body = client.selenium.find_element_by_tag_name('body')
#         span = body.find_element_by_tag_name('span')
#         span.click()
#         client.selenium.close()

#     with mupf.App() as app:
#         client = app.summon_client(frontend=mupf.client.Selenium)
#         createElement = client.window.document.createElement
#         bodyAppendChild = client.window.document.body.appendChild
#         span = bodyAppendChild(createElement('span'))
#         span.innerHTML = "CLICK ME"
#         span.onclick = event_handler

#         app.piggyback_call(userlike_action, client)

#         while client:
#             client.run_one_callback_blocking()

# @istest
# def port_unavailable():
#     """with_selenium/basics: Port already used -> Fail with `OSError` exception
#     """
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     try:
#         sock.bind(('127.0.0.1', mupf.App.default_port))
#     except OSError:
#         raise SkipTest('Required port was unavaliable in the first place')

#     with assert_raises(OSError):
#         with mupf.App():
#             pass
#     sock.close()
