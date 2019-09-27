from mupf import log

@log.loggable('test_1')
def test_func(x, y):
    return x+y

log.enable('out_test.log')

if __name__ == '__main__':

    test_func(4, 7)