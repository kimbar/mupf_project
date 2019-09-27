from mupf import log

@log.loggable('test_1')
def test_func(x, y):
    return x+test_func2(y)

@log.loggable('test_2')
def test_func2(g):
    return g+100

log.enable('out_test.log')

if __name__ == '__main__':

    for k in range(3,5):
        test_func(k, 7)