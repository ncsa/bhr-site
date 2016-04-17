# This settings_local.py file is used for testing
# Specifically it enables the unauthenticated_limited_query option
# @override_settings won't work because I enable the views at import time
# so that should probably be changed to make testing easier
BHR = {
    'time_multiplier':              2.0,
    'time_window_factor':           2.0,
    'minimum_time_window':          43200.0,
    'penalty_time_multiplier':      2.0,
    'return_to_base_multiplier':    2.0,
    'return_to_base_factor':        2.0,
    'unauthenticated_limited_query':  True,
    'local_networks': ['10.0.0.0/8'],
}
