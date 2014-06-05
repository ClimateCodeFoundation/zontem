#!/usr/bin/env python

"""
Data validity.
"""

#: The value that is used to indicate a bad or missing data point.
MISSING = 9999.0

def invalid(v):
    return v == MISSING

def valid(v):
    return not invalid(v)

