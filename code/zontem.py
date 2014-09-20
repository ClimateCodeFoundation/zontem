#!/usr/bin/env python
#
# zontem.py
#
# David Jones, 2010-08-05, revised 2014-06-05
#
# Zonal Temperatures
#
# A simple computation of global average temperature anomaly via zonal
# averages.

"""
zontem.py [--input ghcnm.dat] [--zones 20]
"""

import math
import os
import re
import sys

# ZONTEM
import ghcn
from data import valid, MISSING
import series

parent_dir = os.path.join(os.path.dirname(__file__), '..')
parent_dir = os.path.abspath(parent_dir)

base_year = 1880
combine_overlap = 20

# Maximum length of any input series.
max_series_length = 0

def run(**key):
    import glob
    name = key.get('input', 'v3')

    if name == 'v3':
        input_dir = os.path.join(parent_dir, 'input')
        dat_glob = os.path.join(input_dir, 'ghcnm.v3.*/ghcnm*.dat')
        v3dat = sorted(glob.glob(dat_glob))[-1]
    else:
        v3dat = name
    input = ghcn.M.read(v3dat,
      min_year=base_year,
      MISSING=MISSING)

    N = int(key.get('zones', 20))
    global_annual_series, zonal_annual_series = zontem(input, N)

    # Pick an output file name, which starts with
    # "Zontem" and is followed by the GHCN-M filename
    # with a different file extension.
    basename = os.path.basename(v3dat)
    basename = re.sub(r'[.]dat$', '', basename)
    basename = 'Zontem-' + basename

    output_dir = os.path.join(parent_dir, 'output')
    csv_filename = os.path.join(output_dir, basename + '.csv')

    with open(csv_filename, 'w') as csv_file:
        csv_save(csv_file, global_annual_series, zonal_annual_series)
        sys.stdout.write(csv_filename + '\n')

def zontem(input, n_zones):
    zones = split(input, n_zones)
    zonal_average = map(combine_stations, zones)
    global_average = combine_stations(zonal_average)
    global_annual_average = annual_anomaly(global_average.series)
    zonal_annual_average = [
      annual_anomaly(zonal.series) for zonal in zonal_average]
    return global_annual_average, zonal_annual_average

def split(stations, N=20):
    """
    Split a series of stations into `N` equal area latitudinal zones.
    """

    global max_series_length

    # one list for each zone
    zone = [[] for _ in range(N)]

    for station in stations:
        max_series_length = max(max_series_length, len(station.series))
        # Calculate Z, distance from equatorial plane (normalised).
        z = math.sin(math.radians(station.latitude))
        i = int(math.floor((z+1.0)/2*N))
        # Fix Zone of hypothetical North Pole station.
        i = min(i, N-1)
        zone[i].append(station)
        sys.stderr.write('\rReading station data. Zone %2d: %4d records' % (i, len(zone[i])))
        sys.stderr.flush()
    sys.stderr.write('\n')
    return zone

def combine_stations(stations):
    """
    Takes a list of stations (each with a .series attribute), and
    combine them into one new Station.
    """

    # Number of months in fixed length record.
    M = max_series_length
    # Make sure all the records are the same length, namely *M*.
    combined = [MISSING]*M

    if len(stations) == 0:
        return combined

    def good_months(station):
        count = 0
        for v in station.series:
            if v != MISSING:
                count += 1
        return count

    stations = iter(sorted(stations, key=good_months, reverse=True))

    first_station = stations.next()
    combined[:len(first_station.series)] = first_station.series
    combined_weight = [valid(v) for v in combined]
    log("LONGEST %s %s" % (first_station.id, "1"*12))

    for i,station in enumerate(stations):
        new = [MISSING]*len(combined)
        new[:len(station.series)] = station.series
        months_combined = series.combine(combined, combined_weight,
            new, 1.0,
            combine_overlap)
        sys.stderr.write('\r%d' % i)
        months_used = ''.join(
          "01"[months_combined[i] > 0] for i in range(12))
        log("COMBINE %s %s" % (station.id, months_used))
    sys.stderr.write('\n')
    import ghcn
    return ghcn.Station(series=combined, id="NEW")

def annual_anomaly(monthly):
    """
    Take a monthly series and convert to annual anomaly.  All months
    (Jan to Dec) are required to be present to compute an anomaly
    value.
    """

    # Convert to monthly anomalies...
    means, anoms = series.monthly_anomalies(monthly)
    result = []
    # Then take 12 months at a time and annualise.
    for year in zip(*anoms):
        if all(valid(month) for month in year):
            # All months valid
            result.append(sum(year)/12.0)
        else:
            result.append(MISSING)
    return result

def csv_save(out, global_series, zonal_series):
    """
    Save the global annual series and N zonal annual series,
    as a CSV file.
    """

    import csv

    csvfile = csv.writer(out)
    header = ["Year", "Global Temperature Anomaly (K)"]
    for i in range(len(zonal_series)):
        header.append("Zone %d" % i)
    csvfile.writerow(header)
    for i, values in enumerate(zip(global_series, *zonal_series)):
        row = [base_year + i]
        # `values` has 1 value the global series, and one for each zone.
        for v in values:
            row.append(format1(v))
        csvfile.writerow(row)

def format1(val):
    if not valid(val):
        return ''
    return "{: 7.3f}".format(val)

log_file = None
def log(message):
    global log_file
    if not log_file:
        try:
            os.mkdir("log")
        except OSError:
            pass
        log_file = open(os.path.join("log", "zontem.log"), 'w')
    log_file.write(message + '\n')

def usage(out):
    out.write(__doc__.strip() + '\n')

def main(argv=None):
    import getopt

    if argv is None:
        argv = sys.argv
    opts,arg = getopt.getopt(argv[1:], '',
      ['help', 'input=', 'zones='])
    if arg:
        usage(sys.stderr)
        return 2
    key = {}
    for opt,v in opts:
        if opt == '--help':
            return usage(sys.stdout)
        key[opt[2:]] = v
    run(**key)

if __name__ == '__main__':
    main()
