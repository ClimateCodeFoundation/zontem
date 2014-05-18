#!/usr/bin/env python
#
# zontem.py
#
# David Jones, 2010-08-05
#
# Zonal Temperatures
#
# A simple computation of global average temperature anomaly via zonal
# averages.

import math
import os
import re
import sys

# ZONTEM
import gio
from giss_data import valid, MISSING, Series
import series

base_year = 1880
combine_overlap = 20

# Most recent year of any input record.
last_year = 0

# Meta data
v2inv = os.path.join('input', 'v2.inv')

def run(**key):
    import glob
    name = key.get('input', 'v3')

    if name == 'v3':
        v3dat = glob.glob('input/ghcnm.v3.*/ghcnm*.dat')[0]
    else:
        v3dat = name
    v3meta_filename = re.sub(r'[.]dat$', '.inv', v3dat)
    v3meta = gio.station_metadata(path=v3meta_filename, format='v3')
    input = gio.GHCNV3Reader(v3dat,
      year_min=base_year,
      meta=v3meta,
      MISSING=MISSING)

    N = int(key.get('zones', 20))
    global_annual_series = zontem(input, N)

    # Pick an output file name, which starts with
    # "Zontem" and is followed by the GHCN-M filename
    # with a different file extension.
    basename = os.path.basename(v3dat)
    basename = re.sub(r'[.]dat$', '', basename)
    basename = 'Zontem-' + basename

    save(open(basename + '.txt', 'w'), global_annual_series)
    csv_save(open(basename + '.csv', 'w'), global_annual_series)

def zontem(input, n_zones):
    zones = split(input, n_zones)
    zonal_average = map(combine_records, zones)
    global_average = combine_records(zonal_average)
    annual_series = annual_anomaly(global_average)
    return annual_series

def split(records, N=20):
    """Split a series of records into equal area latitudinal zones."""

    global last_year

    # one list for each zone
    zone = [[] for _ in range(N)]

    for record in records:
        last_year = max(last_year, record.last_year)
        lat = record.station.lat
        # Calculate Z, distance from equatorial plane (normalised).
        z = math.sin(lat*math.pi/180.0)
        i = int(math.floor((z+1)/2*N))
        # Fix Zone of hypothetical North Pole station.
        i = min(i, N-1)
        zone[i].append(record)
        sys.stderr.write('\rZone %2d: %4d records' % (i, len(zone[i])))
        sys.stderr.flush()
    sys.stderr.write('\n')
    return zone

def combine_records(records):
    """
    Takes a list of records, and combine them into one record.
    """

    # Number months in fixed lengh record
    M = 12 * (last_year - base_year + 1)
    # Make sure all the records are the same length, namely *M*.
    combined = [MISSING]*M

    if len(records) == 0:
        return combined

    def good_months(record):
        return record.good_count()

    records = iter(sorted(records, key=good_months, reverse=True))
    first = records.next()

    combined[:len(first.series)] = first.series
    combined_weight = [valid(v) for v in combined]
    for i,record in enumerate(records):
        new = [MISSING]*len(combined)
        new[:len(record.series)] = record.series
        series.combine(combined, combined_weight,
            new, 1.0,
            combine_overlap)
        sys.stderr.write('\r%d' % i)
    sys.stderr.write('\n')
    return Series(first_year=base_year, series=combined)

def annual_anomaly(monthly):
    """Take a monthly series and convert to annual anomaly.  All months
    (Jan to Dec) are required to be present to compute an anomaly
    value."""

    # Convert to monthly anomalies...
    means, anoms = series.monthly_anomalies(monthly.series)
    result = []
    # Then take 12 months at a time and annualise.
    for year in zip(*anoms):
        if all(valid(month) for month in year):
            # All months valid
            result.append(sum(year)/12.0)
        else:
            result.append(MISSING)
    return result

def csv_save(out, series):
    """
    Save an annual series, as a CSV file.
    """

    import csv

    csvfile = csv.writer(out)
    for i, val in enumerate(series):
        if not valid(val):
            val=''
        csvfile.writerow([base_year + i, val])

def save(out, series):
    """Save an annual series.  Same format as GISTEMP GLB.txt format.
    But only just enough so that vischeck.py can read it."""

    def fmt(v):
        s = "%4d" % (v*100)
        if len(s) > 4:
            return '****'
        return s

    for i,val in enumerate(map(fmt, series)):
        year = base_year + i
        out.write(
          ("%04d " + 12*" ****" + "   %4s**** " + 4*" ****" + " %d\n") %
          (year, val, year))


def main(argv=None):
    import getopt

    if argv is None:
        argv = sys.argv
    opts,args = getopt.getopt(argv[1:], '',
      ['input=', 'zones='])
    key = {}
    for opt,v in opts:
        key[opt[2:]] = v
    run(**key)

if __name__ == '__main__':
    main()
