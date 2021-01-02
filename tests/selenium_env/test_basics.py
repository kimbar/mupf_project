import unittest
import os

# Mupf Log Deterministic Identifiers
os.environ['MUPFLOGDETIDS'] = "TRUE"

import sys
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import mupf
import time
import socket
import shutil

class Connection(unittest.TestCase):

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
        "selenium/basics: None -> Run Firefox webdriver (geckodriver) headless"

        options = Options()
        options.headless = True
        driver = webdriver.Firefox(options=options)
        driver.close()

    def test_port_unavailable(self):
        "selenium/basics: Port already used -> Fail with `OSError` exception"

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', mupf.App.default_port))
        except OSError:
            self.skipTest('Required port was unavaliable in the first place')

        with self.assertRaises(OSError) as cm:
            with mupf.App():
                pass
        print('Exception text:', cm.exception)

        sock.close()

    def tearDown(self) -> None:
        print(f'Test run time: {int((time.time()-self.t0)*1000)} ms')


class LowLevelApp(unittest.TestCase):

    def logfile_id(self):
        result = self.id()
        to_trim = os.path.basename(os.path.dirname(__file__))+"."
        where_trim = result.find(to_trim)
        if where_trim != -1:
            result = result[where_trim+len(to_trim):]
        return result

    def setUp(self) -> None:
        print(self.shortDescription())
        os.chdir(os.path.dirname(__file__))

        self.t0 = time.time()

        mupf.log.settings.graph_style = 'default'
        mupf.log.enable(self.logfile_id()+'.RECENT.log')

    def test_hello_world(self):
        "selenium/basics: None -> Display 'Hello, World!' example"

        text = "Hello, World!"
        with mupf.App() as app:
            client = app.summon_client(frontend=mupf.client.Selenium, headless=True)
            client.window.document.body.innerHTML = text

            body = client.selenium.find_element_by_tag_name('body')
            print(f'Text found: {repr(body.text)}')
            self.assertEqual(body.text, text)

    def test_append_element(self):
        "selenium/basics: None -> Create and append a <span>"

        with mupf.App() as app:
            client = app.summon_client(frontend=mupf.client.Selenium, headless=True)
            createElement = client.window.document.createElement
            bodyAppendChild = client.window.document.body.appendChild
            bodyAppendChild(createElement('span'))

            body = client.selenium.find_element_by_tag_name('body')
            span = body.find_element_by_tag_name('span')
            self.assertIsInstance(span, webdriver.remote.webelement.WebElement)

    def _list_to_reason(self, exc_list):
        if exc_list and exc_list[-1][0] is self:
            return exc_list[-1][1]

    def tearDown(self) -> None:
        print(f'Test run time: {int((time.time()-self.t0)*1000)} ms')

        result = self.defaultTestResult()
        self._feedErrorsToResult(result, self._outcome.errors)
        error = self._list_to_reason(result.errors)
        failure = self._list_to_reason(result.failures)
        ok = not error and not failure

        if ok:
            shutil.copy(self.logfile_id()+'.RECENT.log', self.logfile_id()+'.SUCESS.log')

if __name__ == '__main__':
    unittest.main()


# from selenium import webdriver
# import time

# import mupf
# import mupf.exceptions



# @istest




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

