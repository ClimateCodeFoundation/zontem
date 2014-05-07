#!/usr/bin/env python
# $URL$
# $Rev$
#
# statanal.py
#
# Station Analysis
#
# Particular the correlation analysis mentioned in Hansen and Lebedeff
# 1987.

import pathex
from code.giss_data import valid
from code import series

# ZONTEM
import correlation

# http://docs.python.org/release/2.4.4/lib/module-random.html
import random

base_year = 1880

def record_correlation(s, t, overlap=300):
    """Return the correlation between the monthly anomalies of the two
    records, where they have common months."""

    assert s.first_year == t.first_year
    a = list(s.series)
    b = list(t.series)
    series.anomalize(a)
    series.anomalize(b)
    common = [(u,v) for u,v in zip(a, b) if valid(u) and valid(v)]
    if len(common) < overlap:
        return None

    return correlation.pearson(*zip(*common))

def record_list(input='input/v2.mean'):
    from tool import giss_io
    r = giss_io.V2MeanReader(input, year_min=base_year)
    return list(r)

def pairs(records, n=9):
    for _ in range(n):
        s = random.choice(records)
        t = random.choice(records)
        print s.uid, t.uid, record_correlation(s, t)

def main(argv=None):
    import sys
    if argv is None:
        argv = sys.argv
    argv = argv[1:]
    pairs(record_list(), *map(int, argv))

if __name__ == '__main__':
    main()
