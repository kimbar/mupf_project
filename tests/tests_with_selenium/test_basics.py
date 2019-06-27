import nose
from nose.tools import istest, nottest, assert_raises
import socket
from selenium import webdriver

import mupf

@istest
def selenium():
    """with_selenium/basics: None -> Invoke Selenium browser
    """
    driver = webdriver.Firefox()
    driver.close()

@istest
def hello_world():
    """with_selenium/basics: None -> Display "Hello, World!" example
    """
    with mupf.App() as app:
        client = app.summon_client(frontend=mupf.client.Selenium)
        client.window.document.body.innerHTML = "Hello, World!"

@istest
def port_unavailable():
    """with_selenium/basics: Port already used -> Fail with `OSError` exception
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', mupf.App.default_port))

    with assert_raises(OSError):
        with mupf.App():
            pass
            
    sock.close()



