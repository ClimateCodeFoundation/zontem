#!/usr/bin/env python
#
# ghcn.py
#
# 2014-05-18
# David Jones
#
# Originally from ccc-gistemp code written by
# Paul Ollis and David Jones, 2010-03-10


"""
ghcn.M.read() reads GHCN-M v3 datafiles.
"""


import itertools
import re
from collections import defaultdict

class Station(object):
    """A station.

    This holds the series and metadata for a single station.

    The class is completely generic, any properties can be
    stored on the instance by passing them as keyword arguments
    to the constructor.

    In this module, the .series property is used to store a list
    of monthly data values, and other properties are assigned
    from the station metadata read from the .inv file.
    """

    def __init__(self, **values):
        self.__dict__.update(values)

    def __repr__(self):
        return "Station(%r)" % self.__dict__

class M:
    def read(path=None, file=None, min_year=None, MISSING=8888):
        """Reads a file in GHCN-M v3 .dat format and yields each station
        as a Station instance. The instance will have a series
        attribute.

        Station metadata (location, and so on) is read from a file
        with a .inv extension (this is read automatically), and is
        used to populate the attributes of the Station instances that
        are yielded.

        If `year_min` is specified, then only years >= year_min are kept
        (the default, None, keeps all years).
        
        The (integer) values in the file are scaled according to the
        element type. So for TAVG the values stored in the file are
        in units of 0.01 degrees C, but the returned values from
        this function are in degrees C.

        See ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README for format
        of this file.
        """

        # If path is supplied, open it to use an input.
        if path:
            inp = open(path)
        else:
            inp = file

        # Derive meta file location from pathname.
        if not path:
            path = inp.name
        v3meta_filename = re.sub(r'[.]dat$', '.inv', path)
        meta = M.station_metadata(path=v3meta_filename, format='v3')

        def id11(l):
            """Extract the 11-digit station identifier."""
            return l[:11]

        for id,lines in itertools.groupby(inp, id11):
            d = dict(id=id, first_year=min_year)
            if meta.get(id):
                d.update(meta[id])

            series = series_from_lines(lines, MISSING, min_year)

            if len(series) != 0:
                yield Station(series=series, **d)


    def station_metadata(path=None, file=None, format='v3'):
        """
        Read a collection of station metadata from file, return
        it as a dictionary of dictionaries. The returned
        dictionary is keyed by the 11-digit identifier (as a
        string) to give the metadata for that particular
        station.

        *format* specifies the format of the metadata; it can only be
        'v3' (for GHCN-M v3). It exists to provide compatibility
        with an alternate implementation of the same interface.
        """

        # Do not supply both arguments!
        assert not (file and path)

        if path:
            file = open(path)
        assert file

        assert 'v3' == format

        # With the beta GHCN-M v3 metadata, several fields are blank for
        # some stations.  When processed as ints, these will get
        # converted to None.
        def blank_int(s):
            """Convert a field to an int, or if it is blank, convert to
            None."""

            if s.isspace():
                return None
            return int(s)

        # Fields are named after the designators used in the GHCN-M v3
        # documentation.

        # See ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README for format
        # of GHCN's metadata file.
        v3_ghcn_fields = dict(
            id        = (0,    11, str),
            latitude  = (12,   20, float),
            longitude = (21,   30, float),
            stelev    = (31,   37, float),
            name      = (38,   68, str),
            grelev    = (69,   73, blank_int),
            popcls    = (73,   74, str),
            popsiz    = (75,   79, blank_int),
            topo      = (79,   81, str),
            stveg     = (81,   83, str),
            stloc     = (83,   85, str),
            ocndis    = (85,   87, blank_int),
            airstn    = (87,   88, str),
            towndis   = (88,   90, blank_int),
            grveg     = (90,  106, str),
            popcss    = (106, 107, str),
        )

        fields = v3_ghcn_fields

        result = {}
        for line in file:
            d = dict((field, convert(line[a:b]))
                      for field, (a,b,convert) in fields.items())
            result[d['id']] = d

        return result

def series_from_lines(lines, MISSING, min_year):
    all_missing = [MISSING]*12

    # Make a dictionary that maps from year to the 12 data
    # values for that year. Use a default of 12 MISSING values.
    d = defaultdict(lambda:all_missing)
    for line in lines:
        year = int(line[11:15])
        element = line[15:19]
        multiplier = ELEMENT_SCALE[element]
        values = [convert_single(line[i:i+8], multiplier, MISSING)
          for i in range(19,115,8)]
        if values != all_missing:
            d[year] = values

    # Convert the dictionary to a single list.
    l = []
    if min_year is not None:
        start = min_year
    else:
        start = min(d)
    for year in range(start, max(d)+1):
        l.extend(d[year])
    return l

ELEMENT_SCALE = dict(TAVG=0.01, TMIN=0.01, TMAX=0.01)

def convert_single(s, multiplier, MISSING):
    """
    Convert single value. *s* is the 8 character string: 5
    characters for value, 3 for flags. Non-MISSING values are
    multiplied by *multiplier*.
    """

    # Quality-control flags that cause value to be rejected.
    # :todo: make parameter.  When using the QCA dataset
    # we shouldn't actually see any of these flags.
    reject = 'DKOSTW'

    v = int(s[:5])
    # Flags for Measurement (missing days), Quality, and
    # Source.
    m,q,s = s[5:8]
    if q in reject or v == -9999:
        return MISSING
    v *= multiplier
    return v

# We'd like to access ghcn.M.thing as a function, not a
# bound method. This piece of code arranges that. Not
# very elegantly.

class Instance:
    def __init__(self, **k):
        self.__dict__.update(k)

M = Instance(**M.__dict__)
