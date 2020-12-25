from mupf import log
import threading
import time

@log.loggable('test_1')
def test_func(x, y):
    time.sleep(x)
    return x+test_func2(y)

@log.loggable('test_2')
def test_func2(g):
    return g+100




@log.loggable('test.py/K<obj>', log_path=False)
class K:

    @log.loggable('test_init', log_exit=False)
    def __init__(self, x):
        self._x = x

    @log.loggable('test_method')
    def met(self, a):
        return test_func(0., a)

    @property
    @log.loggable('test_prop_x.:', log_enter=False)
    def x(self):
        return self._x

    @x.setter
    @log.loggable('test_prop_x.=', log_exit=False)
    def x(self, value):
        self._x = value


# log.enable('out_test.log', graph_style='rounded')
log.enable('out_test.log')

T = threading.Thread(name='Server', target=test_func, args=(0.01,89))

if __name__ == '__main__':

    for k in range(3,5):
        test_func(0., 7)

    k = K(34)
    T.start()
    w = K(123)
    k.met(2009)
    w.met(-100)

    w.x = 783612

    u = w.x + k.x