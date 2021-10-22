# ================= Unit Test checks
print("Start Evaluation Unit Tests................................................................")
import os
import sys
import pandas as pd
import numpy as np
import pytest


from utils import *

### check for Rejected orders
IS_LIVE=eval(os.environ["IS_LIVE"])
LOG = sys.argv[-1]
print("-----------------LOG",LOG)
print(f"log={LOG}","starting checks....................")
d=open_logs_to_df(file=LOG)

# check 1

def test_check1__has_expired_bars():
    assert check_log(file=LOG,string="EXPIRED") == True

def test_check3__positions_must_be_equal_mainorders():
    n_position_open = d.query("event=='position_open'").shape[0]
    n_notify_orders_completed_all = d.query("status=='Completed' & label=='main'").shape[0]
    assert n_position_open == n_notify_orders_completed_all, f"check1: 'event=position_open' ({n_position_open}) must be equal to number notify_orders with label=main, status=completed ({n_notify_orders_completed_all})"

def test_check4__canceledstops_must_be_euqal_canceledstoporders():
    n_cancel_stop = d.query("event=='cancel_stop'").shape[0]
    n_notify_orders_canceled = d.query("status=='Canceled' & type=='Stop' ").shape[0]
    assert n_cancel_stop == n_notify_orders_canceled, f"check2: 'event=cancel_stop' ({n_cancel_stop}) must be equal to number notify_orders, status=Canceled ({n_notify_orders_canceled})"
    
def test_check5__expiredpositions_must_be_equal_completedexpiredorders():
    n_position_expired = d.query("event=='position_expired'").shape[0]
    n_notify_orders_completed_main = d.query("status=='Completed' & label=='expiration' ").shape[0]
    assert n_position_expired == n_notify_orders_completed_main ,f"'check3: event=position_expired' ({n_position_expired}) must be equal to number notify_orders, status=Completed and label=expiration ({n_notify_orders_completed_main})"









