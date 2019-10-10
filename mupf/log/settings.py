import logging

MIN_COLUMN_WIDTH : int = 90    # minimum width of the column with names of functions
TAB_WIDTH : int = 20           # if the width is not enough, this much is added in one go
GROUP_WIDTH : int = 10
GROUP_NAME_WIDTH : int = 4

graph_style : str = 'default'
logging_format : str = '[%(name)s] %(message)s'
logging_level = logging.INFO
log_state_of_switched_off_managers = False
print_group_name = True
print_tracks = True
print_address = True
print_ruler = True