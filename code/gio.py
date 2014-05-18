#!/usr/bin/env python
#
# gio.py
#
# 2014-05-18
# David Jones
#
# Originally from ccc-gistemp code written by
# Paul Ollis and David Jones, 2010-03-10


"""
Input/Output.  Reader and writer for GHCN-M v3 datafiles.
"""


import itertools

# Clear Climate Code
import giss_data

def GHCNV3Reader(path=None, file=None,
  meta={},
  year_min=None,
  MISSING=8888,
  scale=None):
    """Reads a file in GHCN V3 .dat format and yields each station
    record (as a giss_data.Series instance).

    If a *meta* dict is supplied then the Series instance will have its
    "station" attribute set to value corresponding to the 11-digit ID in
    the *meta* dict.

    If `year_min` is specified, then only years >= year_min are kept
    (the default, None, keeps all years).
    
    If *scale* is specified then the (integer) values in the file are
    multiplied by *scale* before being returned.  When it is not
    specified (the normal case), the scale is derived from the element
    specified in the file (normally for monthly means this is "TAVG" and
    the scale implied by that is 0.01 (degrees C)).

    See ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README for format
    of this file.
    """

    if path:
        inp = open(path)
    else:
        inp = file

    def id11(l):
        """Extract the 11-digit station identifier."""
        return l[:11]

    noted_element = False
    def note_element(element):
        """Print the meteorological element we are reading."""
        friendly = dict(TAVG='average temperature',
          TMIN='mean minimum temperature',
          TMAX='mean maximum temperature')
        print "(Reading %s)" % friendly[element]

    element_scale = dict(TAVG=0.01, TMIN=0.01, TMAX=0.01)
    # Quality-control flags that cause value to be rejected.
    # :todo: make parameter.  When using the QCA dataset
    # we shouldn't actually see any of these flags.
    reject = 'DKOSTW'

    def convert(s):
        """Convert single value. *s* is the 8 character string: 5
        characters for value, 3 for flags."""

        # This function captures *multiplier* which can, in principle,
        # change for each line.

        v = int(s[:5])
        # Flags for Measurement (missing days), Quality, and
        # Source.
        m,q,s = s[5:8]
        if q in reject or v == -9999:
            v = MISSING
        else:
            v *= multiplier
        return v

    all_missing = [MISSING]*12

    for id,lines in itertools.groupby(inp, id11):
        key = dict(uid=id, first_year=year_min)
        if meta.get(id):
            key['station'] = meta[id]
        record = giss_data.Series(**key)
        for line in lines:
            year = int(line[11:15])
            element = line[15:19]
            if not noted_element:
                note_element(element)
                noted_element = True
            if scale:
                multiplier = scale
            else:
                multiplier = element_scale[element]
            values = [convert(line[i:i+8]) for i in range(19,115,8)]
            if values != all_missing:
                record.add_year(year, values)
        if len(record) != 0:
            yield record

class GHCNV3Writer(object):
    """Write a file in GHCN v3 format. See also GHCNV3Reader.  The
    format is documented in
    ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README .  If the records
    have an 'element' property, then that is used for the 'element'
    field in the GHCN V3 file, otherwise 'TAVG' is used.
    """

    def __init__(self, path=None, file=None, MISSING=8888, scale=0.01, **k):
        if path is not None:
            self.f = open(path, "w")
        else:
            self.f = file
        self.scale = scale

    def to_text(self, t):
        if t == MISSING:
            return "-9999"
        else:
            return "%5d" % t

    def write(self, record):
        """Write an entire record out."""
        for year in range(record.first_year, record.last_year + 1):
            if not record.has_data_for_year(year):
                continue
            element = getattr(record, 'element', 'TAVG')
            self.writeyear(record.uid, element, year, record.get_a_year(year))

    def writeyear(self, uid, element, year, temps):
        """Write a single year's worth of data out.  *temps* should
        contain 12 monthly values."""

        if len(uid) > 11:
            # Convert GHCN v2 style identifier into 11-digit v3
            # identifier; use 12th digit for the source flag.
            assert len(uid) == 12
            sflag = uid[11]
        elif len(uid) == 6:
            # Assume it's a 6 digit identifier from USHCN.
            uid = '42500' + uid
            sflag = 'U'
        else:
            sflag = ' '
        id11 = "%-11.11s" % uid
        assert len(element) == 4

        tstrings = [self.to_text(t)
                   for t in internal_to_external(temps, scale=self.scale)]
        flags = ['  ' + sflag] * 12

        self.f.write('%s%04d%s%s\n' % (id11, year, element,
          ''.join(t+flag for t,flag in zip(tstrings,flags))))

    def close(self):
        self.f.close()


def station_metadata(path=None, file=None, format='v3'):
    """Read station metadata from file, return it as a dictionary.
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

    # With the beta GHCN V3 metadata, several fields are blank for some
    # stations.  When processed as ints, these will get converted to
    # None."""
    def blank_int(s):
        """Convert a field to an int, or if it is blank, convert to
        None."""

        if s.isspace():
            return None
        return int(s)

    # Fields are named after the designators used in the GHCN v3
    # documentation except for:
    # uid (GHCN: ID), lat (GHCN: latitude), lon (GHCN: longitude).

    # See ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README for format
    # of GHCN's metadata file.
    v3_ghcn_fields = dict(
        uid=    (0,    11, str),
        lat=    (12,   20, float),
        lon=    (21,   30, float),
        stelev= (31,   37, float),
        name=   (38,   68, str),
        grelev= (69,   73, blank_int),
        popcls= (73,   74, str),
        popsiz= (75,   79, blank_int),
        topo=   (79,   81, str),
        stveg=  (81,   83, str),
        stloc=  (83,   85, str),
        ocndis= (85,   87, blank_int),
        airstn= (87,   88, str),
        towndis=(88,   90, blank_int),
        grveg=  (90,  106, str),
        popcss= (106, 107, str),
    )

    fields = v3_ghcn_fields

    result = {}
    for line in file:
        d = dict((field, convert(line[a:b]))
                  for field, (a,b,convert) in fields.items())
        result[d['uid']] = giss_data.Station(**d)

    return result
