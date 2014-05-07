#!/usr/bin/env python
# $URL$
# $Rev$
#
# pairdist.py
#
# Take output of statanal.py, and augment with distance and direction
# vectors.

import pathex
from code import giss_data
from tool.ncartotext import iso6709

import math

station = giss_data.stations()

# Ignore stations separated by more than this (km).
cutoff = 5000

def doit(input='correlations', out=None):
    import sys
    if out is None:
        out = sys.stdout
    f = open(input)

    dup = set([])

    for row in f:
        id12s,id12t,corr = row.split()
        if corr == "None":
            continue
        id11s = id12s[:11]
        id11t = id12t[:11]
        if id11s == id11t:
            continue
        s = station[id11s]
        t = station[id11t]
        d = distance(s, t)
        if d > 5000:
            continue
        if (id12s,id12t) in dup:
            continue
        dup.add((id12s,id12t))
        vec = direction(s, t)
        row = row.strip()
        print >> out, row, iso6709(s.lat, s.lon), iso6709(t.lat, t.lon), \
          d, vec[0], vec[1]

def distance(s, t):
    """Distance between two stations."""
    # Clear Climate Code
    from code import earth

    return earth.radius * angular_separation(s, t)

def direction(s, t):
    """(unit) direction vector from s to t."""
    dlon = t.lon - s.lon
    if dlon > 180:
        dlon -= 360
    if dlon < -180:
        dlon += 360
    assert -180 <= dlon <= 180
    dlat = t.lat - s.lat
    if dlat == dlon == 0:
        return (0,0)
    r = math.hypot(dlon, dlat)
    return dlon/r, dlat/r

def angular_separation(s, t):
    """Return the angular separation, in radians, between two
    stations."""

    def cos(deg):
        return math.cos(deg*math.pi/180.0)
    def sin(deg):
        return math.sin(deg*math.pi/180.0)

    # Dot product of 3-vector gives cosine of angle.
    costheta = (sin(s.lat)*sin(t.lat) + cos(s.lat)*cos(t.lat)*
      (cos(s.lon)*cos(t.lon) + sin(s.lon)*sin(t.lon)))
    costheta = min(costheta, 1.0)
    costheta = max(costheta, -1.0)
    return math.acos(costheta)

def main(argv=None):
    import sys
    if argv is None:
        argv = sys.argv
    doit()

if __name__ == '__main__':
    main()
