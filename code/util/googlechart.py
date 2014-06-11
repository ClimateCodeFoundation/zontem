#!/usr/bin/env python

import csv
import math
import urllib
import sys

def chart(file):
    csv_file = csv.reader(file)
    rows = list(csv_file)
    years = [row[0] for row in rows]
    values = [row[1] for row in rows]
    valid_values = [float(x) for x in values if x != '']
    min_year = min(years)
    max_year = max(years)
    min_value = min(valid_values)
    max_value = max(valid_values)

    # Round up to the next 0.5 (and scale by 100)
    max_y = int(math.ceil(max_value * 2)) * 50
    # Round down to the next 0.5 (and scale by 100)
    min_y = int(math.floor(min_value * 2)) * 50
    chds = "{},{}".format(min_y, max_y)

    vs = [str(int(round(float(v) * 100))) if v != '' else '-999' for v in values]

    chd = "t:{}".format(",".join(vs))

    param = dict(cht='lc', chs='400x300', chds=chds, chd=chd)
    print("https://chart.googleapis.com/chart?{}".format(
      urllib.urlencode(param)))

def main(argv=None):
    if argv is None:
       argv = sys.argv

    arg = argv[1:]
    if len(arg) == 0:
        file = sys.stdin
    else:
        file = open(arg[0])
    chart(file)

if __name__ == '__main__':
    main()
