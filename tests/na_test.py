from mupf.log import new_approach

@new_approach.loggable()
def test_func(x, y):
    return x+y

new_approach.LogManager._managers_by_addr['test_func'].on()

if __name__ == '__main__':

    test_func(4, 7)