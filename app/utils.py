import os
import sys
import pandas as pd
import numpy as np
import pytest


def open_logs_to_df(file="backtrader.log"):
    logs = []
    with open(file) as myfile:
        for line in myfile:
            if "=" in line and "|" in line and not "connected to:" in line:
                s = line.split(" | ")
                if len(s) <= 1: continue
                d = { e.split("=")[0]:e.split("=")[1].strip() for e in s[1:] }
                logs.append(d)
    d = pd.DataFrame(logs)
    print("logfile opened",file,'with cols:')
    print(d.columns)
    return d

def check_log(file,string):
    with open(file) as myfile:
        for line in myfile:
            if string in line:
                return True
    return False