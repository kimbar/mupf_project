import logging

MIN_COLUMN_WIDTH : int = 90    # minimum width of the column with names of functions
TAB_WIDTH : int = 20           # if the width is not enough, this much is added in one go
GROUP_WIDTH : int = 10

graph_style : str = 'default'
logging_format : str = '[%(name)s] %(message)s'
logging_level = logging.INFO