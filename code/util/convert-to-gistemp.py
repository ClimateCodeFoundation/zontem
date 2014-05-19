#!/usr/bin/env python

"""
Convert from .csv to .txt in same format as GISTEMP.

vischeck.py can be run on the output of this program.
"""

import sys

def as_gistemp(out, series):
    """Save an annual series.  `series` should be a sequence of
    (year, value) pairs.
    
    Output is same format as GISTEMP GLB.txt format.
    But only just enough so that vischeck.py can read it.
    """

    def fmt(v):
        if v is None:
            return '****'
        s = "{:4.0f}".format(v*100)
        if len(s) > 4:
            return '****'
        return s

    for year,v in series:
        formatted_value = fmt(v)
        out.write(
          ("%04d " + 12*" ****" + "   %4s**** " + 4*" ****" + " %d\n") %
          (year, formatted_value, year))

def float_or_None(s):
    if s == '':
        return None
    return float(s)

def pairs_from_csv(input):
    import csv
    for row in csv.reader(input):
        yield int(row[0]), float_or_None(row[1])

def main():
    as_gistemp(sys.stdout, pairs_from_csv(sys.stdin))

if __name__ == '__main__':
    main()
