from mupf import log

@log.loggable('test_1')
def test_func(x, y):
    return x+test_func2(y)

@log.loggable('test_2')
def test_func2(g):
    return g+100


@log.loggable('test.py/K<obj>', log_path=False)
class K:
    
    @log.loggable('test_init')
    def __init__(self, x):
        self._x = x

    @log.loggable('test_method')
    def met(self, a):
        return test_func(self._x, a)


log.enable('out_test.log')
print(log._manager.LogManager._managers_by_addr)

if __name__ == '__main__':

    for k in range(3,5):
        test_func(k, 7)

    k = K(34)
    w = K(123)
    k.met(2009)
    w.met(-100)