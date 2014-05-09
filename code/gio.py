#!/usr/bin/env python
# $URL: http://ccc-gistemp.googlecode.com/svn/trunk/tool/gio.py $
# $Rev: 1020 $
#
# gio.py
#
# Paul Ollis and David Jones, 2010-03-10
#
# (was previously called giss_io.py, then io.py)

"""GISTEMP Input/Output.  Readers and writers for datafiles used by NASA
GISS GISTEMP.

Some of these file formats are peculiar to GISS, others are defined and
used by other bodies (such as NOAA's v2.mean format).
"""
__docformat__ = "restructuredtext"


import glob
import itertools
import math
import os
import re
import struct
import warnings


# Clear Climate Code
import giss_data


#: Integer code used to indicate missing data.
#:
#: This is units of 0.1 celsius. This code is only used when
#: reading or writing input and working files.
MISSING = 9999

# For all plausible integers, converting them from external to internal
# to external again will preserve their value.
def tenths_to_float(t):
    if t == MISSING:
        return code.giss_data.MISSING
    return t * 0.1

# TODO: How does this differ from float_to_tenths.
#       Answer:
#           float_to_tenths(-0.95) == -10
#           as_tenths(-0.95) == -9
# Note: only used by obsolete file formats.
def as_tenths(v):
    return int(math.floor(v * 10 + 0.5))


# TODO: Probably should be a generator.
def internal_to_external(series, scale=0.1):
    """Convert a series of values to external representation by
    converting to integer tenths (or other scale).  Normally
    this is used to convert a series from degrees Celcius to tenths
    of a degree.

    :Param series:
        A list or iterable of floating point value; usually each value
        represents a temperature in Celsius.

    :Return:
        A new list of values (ints).

    """

    # Note: 1/0.1 == 10.0; 1/0.01 == 100.0 (in other words even though
    # 0.1 and 0.01 are not stored exactly, their reciprocal is exactly
    # an integer)
    scale = 1.0/scale

    def toint(f):
        # :todo: Use of abs() probably not needed.
        if abs(f - code.giss_data.MISSING) < 0.01:
            return MISSING
        return int(round(f * scale))

    return [toint(v) for v in series]

# TODO: Probably should be a generator.
def convert_tenths_to_float(tenths_series):
    """The inverse of `internal_to_external`."""
    return [tenths_to_float(v) for v in tenths_series]


def open_or_uncompress(filename):
    """Opens the text file `filename` for reading.  If this fails then
    it attempts to find a compressed version of the file by appending
    '.gz' to the name and opening that (uncompressing it on
    the fly).

    """
    try:
        return open(filename)
    except IOError:
        # When none of filename, nor filename.gz exists we
        # want to pretend that the exception comes from the original
        # call to open, above.  Otherwise the user can be confused by
        # claims that "foo.gz" does not exist when they tried to open
        # "foo".  In order to maintain this pretence, we have to get
        # the exception info and save it. See
        # http://blog.ianbicking.org/2007/09/12/re-raising-exceptions/
        import sys
        exception = sys.exc_info()
        try:
            import gzip
            return gzip.open(filename + '.gz')
        except IOError:
            pass
        raise exception[0], exception[1], exception[2]


def GHCNV3Reader(path=None, file=None, meta=None, year_min=None, scale=None):
    """Reads a file in GHCN V3 .dat format and yields each station
    record (as a giss_data.Series instance).  For now, this treats
    all the data for a station as a single record (contrast with GHCN V2
    which could have several "duplicates" for a single station).

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
        key = dict(uid=id+'0',
                   first_year=year_min,
                   )
        if meta and meta.get(id):
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

    def __init__(self, path=None, file=None, scale=0.01, **k):
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


def GHCNV2Reader(path=None, file=None, meta=None, year_min=None):
    """Reads a file in GHCN v2.mean format and yields each station.

    If a *meta* dict is supplied then the Series instance will have its
    "station" attribute set to value corresponding to the 11-digit ID in
    the *meta* dict.
    
    If `year_min` is specified, then only years >= year_min are kept
    (the default, None, keeps all years).

    Traditionally a file in this format was the output of Step 0 (and
    of course the format used by the GHCN source), but modern ccc-gistemp
    produces this format for the outputs of Steps 0, 1, and 2."""

    if path:
        f = open(path)
    else:
        f = file

    def id12(l):
        """Extract the 12-digit station record identifier."""
        return l[:12]

    def v2_float(s):
        """Convert a single datum from string to float; converts missing
        values from their V2 representation, "-9999", to internal
        representation, giss_data.MISSING; scales temperatures to
        convert them from integer tenths to fractional degrees C.
        """

        if "-9999" == s:
            return code.giss_data.MISSING
        else:
            return float(s) * 0.1

    # The Series.add_year protocol assumes that the years are in
    # increasing sequence.  This is so in the v2.mean file but does not
    # seem to be documented (it seems unlikely to change either).

    # Group the input file into blocks of lines, all of which share the
    # same 12-digit ID.
    for (id, lines) in itertools.groupby(f, id12):
        key = dict(uid=id, first_year=year_min)
        # 11-digit station ID.
        stid = id[:11]
        if meta and meta.get(stid):
            key['station'] = meta[stid]
        record = code.giss_data.Series(**key)
        prev_line = None
        for line in lines:
            if line != prev_line:
                year = int(line[12:16])
                temps = [v2_float(line[a:a+5]) for a in range(16, 16+12*5, 5)]
                record.add_year(year, temps)
                prev_line = line
            else:
                print ("NOTE: repeated record found: Station %s year %s;"
                       " data are identical" % (line[:12],line[12:16]))

        if len(record) != 0:
            yield record

    f.close()


class GHCNV2Writer(object):
    """Write a file in GHCN v2.mean format. See also GHCNV2Reader."""

    def __init__(self, path=None, file=None, scale=0.1, **k):
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
            self.writeyear(record.uid, year, record.get_a_year(year))

    def writeyear(self, uid, year, temps):
        """Write a single year's worth of data out.  *temps* should
        contain 12 monthly values."""

        strings = [self.to_text(t)
                   for t in internal_to_external(temps, scale=self.scale)]
        self.f.write('%s%04d%s\n' % (uid, year, ''.join(strings)))

    def close(self):
        self.f.close()

def DecimalReader(path, year_min=-9999):
    """Reads a file in Decimal format and yields each station.
    
    If `year_min` is specified, then only years >= year_min are kept
    (the default, -9999, effectively keeps all years).
    """

    f = open(path)
    def id12(l):
        """Extract the 12-digit station record identifier."""
        return l[:12]

    def readt(s):
        v = float(s)
        if v == -9999:
            return MISSING
        return v

    for (id, lines) in itertools.groupby(f, id12):
        # lines is a set of lines which all begin with the same 12
        # character id
        record = code.giss_data.Series(uid=id)
        prev_line = None
        for line in lines:
            if line != prev_line:
                year = int(line[12:16])
                if year >= year_min:
                    temps = [readt(n) for n in line[16:].split()]
                    record.add_year(year, temps)
                prev_line = line
            else:
                print ("NOTE: repeated record found: Station %s year %s;"
                       " data are identical" % (line[:12],line[12:16]))

        if len(record) != 0:
            yield record

    f.close()


class DecimalWriter(object):
    """Decimal is a novel text file format, very similar to GHCN
    v2.mean format.  Each lines conists of a 12 digit record identifier
    immediately followed by a 4 digit year, then followed by the decimal
    temperature values (in degrees C) for the 12 months of the year,
    with each temperature value preceded by a space.  Missing data are
    marked with -9999."""

    def __init__(self, path):
        self.f = open(path, "w")

    def to_text(self, t):
        if t == MISSING:
            return '-9999'
        return repr(t)

    def write(self, record):
        for year in range(record.first_year, record.last_year + 1):
            if not record.has_data_for_year(year):
                continue
            temps = [self.to_text(t) for t in record.get_a_year(year)]
            self.f.write('%s%04d %s\n' % (record.uid, year, ' '.join(temps)))

    def close(self):
        self.f.close()


# :todo: read_antarctic and read_australia are probably too similar.
# :todo: read_antarctic and read_australia would probably benefit from
# itertools.groupby

antarc_discard_re = re.compile(r'^$|^Get |^[12A-Z]$')
antarc_temperature_re = re.compile(r'^(.*) .* *temperature')

def read_antarctic(path, station_path, discriminator,
  meta=None, year_min=None):
    stations = read_antarc_station_ids(station_path, discriminator)
    record = None
    for line in open(path):
        if antarc_discard_re.search(line):
            continue
        station_line = antarc_temperature_re.match(line)
        if station_line:
            station_name = station_line.group(1)
            station_name = station_name.replace('\\','')
            id12 = stations[station_name]
            if record is not None:
                yield record
            key = dict(uid=id12, first_year=year_min)
            id11 = id12[:11]
            if meta and meta.get(id11):
                key['station'] = meta[id11]
            record = code.giss_data.Series(**key)
            continue
        line = line.strip()
        if line.find('.') >= 0 and line[0] in '12':
            year, data = read_antarc_line(line)
            if year >= code.giss_data.BASE_YEAR:
                record.add_year(year, data)

    if record is not None:
        yield record


austral_discard_re = re.compile(r'^$|:')
austral_header_re = re.compile(r'^\s*(.+?)  .*(E$|E )')

def read_australia(path, station_path, discriminator,
  meta=None, year_min=None):
    stations = read_antarc_station_ids(station_path, discriminator)
    record = None
    for line in open(path):
        if austral_discard_re.search(line):
            continue
        station_line = austral_header_re.match(line)
        if station_line:
            station_name = station_line.group(1).strip()
            id12 = stations[station_name]
            if record is not None:
                yield record
            key = dict(uid=id12, first_year=year_min)
            id11 = id12[:11]
            if meta and meta.get(id11):
                key['station'] = meta[id11]
            record = code.giss_data.Series(**key)
            continue
        line = line.strip()
        if line.find('.') >= 0 and line[0] in '12':
            year, data = read_antarc_line(line)
            if year >= code.giss_data.BASE_YEAR:
                record.add_year(year, data)

    if record is not None:
        yield record

def read_antarc_line(line):
    """Convert a single line from the Antarctic/Australasian dataset
    files into a year and a 12-tuple of floats (the temperatures in
    Centigrade).
    """

    year = int(line[:4])
    line = line[4:]
    tuple = []
    if line[6] == '.' or line[7] == '-':
        # Some of the datasets are 12f8.1 with missing values as '       -'.
        for i in range(0,12):
            tuple.append(read_float(line[i*8:i*8+8]))
    else:
        # Others are xx12f7.1 or xxx12f7.1 with missing values as '       '.
        np = line.find('.')
        if np < 0:
            raise ValueError, "Non-data line encountered: '%s'" % line
        position = (np % 7) + 2
        for i in range(0,12):
            tuple.append(read_float(line[i*7+position:i*7+7+position]))
    return (year, tuple)


def read_antarc_station_ids(path, discriminator):
    """Reads a SCARs station ID files and returns a dictionary
    mapping station name to the 12-digit station ID.
    """

    dict = {}
    for line in open(path):
        id11 = line[:11]
        station = line[12:42].strip()
        dict[station] = id11 + discriminator
    return dict


def convert_USHCN_id(record_stream, stations, meta={}):
    """Convert records in *record_stream* from having (6-digit)
    USHCN identifiers to having (12-digit) GHCN identifiers.  Any record
    that has a key in the *stations* dictionary will have its identifier
    ('uid' property) changed to the corresponding value; it will also
    have station metadata added if it's new identifier is in the *meta*
    dictionary."""

    for record in record_stream:
        id12 = stations.get(int(record.uid))
        if id12:
            record.uid = id12
            id11 = id12[:11]
            if id11 in meta:
                record.station = meta[id11]
        yield record

def convert_F_to_C(record_stream):
    """Convert each of the series from degrees Fahrenheit to degrees
    Celsius."""

    def convert_datum(x):
        if code.giss_data.invalid(x):
            return x
        # degrees F to degrees C
        return (x - 32) * 5 / 9.0

    for record in record_stream:
        record.set_series(record.first_month,
          map(convert_datum, record.series))
        yield record

def read_USHCN(path, meta={}):
    """Open the USHCN V2 file *path* and yield a series of temperature
    records.  Each record is in degrees Fahrenheit (the unit used in the
    USHCN files), and will have its `uid` attribute set to its USHCN
    identifier.  Any station metadata from the *meta* dict (keyed by
    station identifier) will be attached to the 'station' property.

    Data marked as missing (-9999 in the USHCN file) or flagged with 'E'
    or 'Q' will be replaced with MISSING.
    """

    def id6(l):
        """The 6 digit USHCN identifier."""
        return l[0:6]

    noted_element = False
    def note_element(element):
        """Print the meteorological element we are reading."""
        # See ftp://ftp.ncdc.noaa.gov/pub/data/ushcn/v2/monthly/readme.txt
        assert element in '1234'
        element = {'1':'mean maximum temperature',
                   '2':'mean minimum temperature',
                   '3':'average temperature',
                   '4':'precipitation',
                  }[element]
        print "(Reading %s)" % element

    prev_element = None
    for id,lines in itertools.groupby(open_or_uncompress(path), id6):
        record = code.giss_data.Series(uid=id,
          first_year=code.giss_data.BASE_YEAR)
        lines = list(lines)
        elements = set(line[6] for line in lines)
        assert len(elements) == 1, "Multiple elements for station %s." % id
        element = elements.pop()
        record.element = USHCN_element_as_GHCN(element)
        if element != prev_element:
            note_element(element)
            prev_element = element
        # '1', '2', '3' indicate (max, min, average) temperatures.
        assert element in '123'
        if id in meta:
            record.station = meta[id]
        for line in lines:
            year = int(line[7:11])
            temps = []
            valid = False
            for m in range(0,12):
                temp_fahrenheit = int(line[m*7+11:m*7+17])
                flag = line[m*7+17]
                if ((flag in 'EQ') or              # interpolated data
                    (temp_fahrenheit == -9999)):   # absent data
                    temp = code.giss_data.MISSING
                else:
                    # Convert to (fractional) degrees F
                    temp = temp_fahrenheit / 10.0
                    valid = True
                temps.append(temp)
            if valid: # some valid data found
                record.add_year(year, temps)
        yield record

def USHCN_element_as_GHCN(element):
    """Convert a USHCN v2 element code to its GHCN v3 counterpart."""

    # According to ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README only
    # the TAVG code is used in GHCN v3 currently (the product is in
    # beta).
    return {
      '1': 'tmax',
      '2': 'tmin',
      '3': 'TAVG',
      '4': 'pcpt',
    }[element]

def read_USHCN_converted(path, stations, meta=None):
    """Read the USHCN data in the file *path*, converting each record to
    degrees Celsius, and converting their station identifiers to use the
    12-digit GHCN identifiers specified in the *stations* dict.
    """

    ushcn = read_USHCN(path, meta)
    celsius = convert_F_to_C(ushcn)
    ghcn_ids = convert_USHCN_id(celsius, stations, meta)
    return ghcn_ids


def read_USHCN_stations(ushcn_v1_station_path, ushcn_v2_station_path):
    """Reads the USHCN station list and returns a dictionary
    mapping USHCN station ID (integer) to 12-digit GHCN record ID
    (string).
    """

    stations = {}
    for line in open(ushcn_v1_station_path):
        (USHCN_id, id11, duplicate) = line.split()
        USHCN_id = int(USHCN_id)
        if not id11.startswith('425'):
            # non-US country_code
            raise ValueError, "non-425 station found in ushcn.tbl: '%s'" % line
        if duplicate != '0':
            raise ValueError, "station in ushcn.tbl with non-zero duplicate: '%s'" % line
        stations[USHCN_id] = id11 + '0'
    # some USHCNv2 station IDs convert to USHCNv1 station IDs:
    for line in open(ushcn_v2_station_path):
        (v2_station,_,v1_station,_) = line.split()
        stations[int(v2_station)] = stations[int(v1_station)]
    return stations


def station_metadata(path=None, file=None, format='v3'):
    """Read station metadata from file, return it as a dictionary.
    *format* specifies the format of the metadata can be:
    'v2' for GHCN v2 (with some GISTEMP modifications);
    'v3' for GHCN v3 (with some GISTEMP modifications);
    'ushcnv2' for USHCN v2.

    GHCN v2

    For GHCN v2 the input file is nearly in the same format as the
    GHCN v2 file v2.temperature.inv (it has extra fields for satellite
    brightness and extra records for 1 US station and several Antarctic
    stations that GHCN doesn't have).

    Descriptions of that file's format can be found in the Fortran programs:
    ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v2/v2.read.inv.f
    ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v2/v2.read.data.f

    Here are two typical lines, with a record diagram

    id---------xname--------------------------xlat---xlon----x1---2----34----5-6-7-8-910grveg-----------GU--11
    0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345
    40371148001 ALMASIPPI,MA                    49.55  -98.20  274  287R   -9FLxxno-9x-9COOL FIELD/WOODSA1   0
    42572530000 CHICAGO/O'HARE, ILLINOIS        42.00  -87.90  205  197U 6216FLxxno-9A 1COOL CROPS      C3 125

       uid                 40371148001          42572530000
          The unique ID of the station. This is held as an 11 digit string.
       name                ALMASIPPI,MA         CHICAGO/O'HARE, ILLINOIS
        The station's name.
       lat                 49.55                42.00
        The latitude, in degrees (two decimal places).
       lon                 -98.20               -87.90
        The longitude, in degrees (two decimal places).
    1  stelev              274                  205
        The station elevation in metres.
    2  grelev              287                  197
        The grid elevation in metres (value taken from gridded dataset).
    3  popcls              R                    U
        'R' for rural,  'S' for semi-urban, 'U' for urban.
    4  popsiz              -9                   6216
        Population of town in thousands.
    5  topo                FL                   FL
        The topography.
    6  stveg               xx                   xx
    7  stloc               no                   no
        Whether the station is near a lake (LA) or ocean (OC).
    8  ocndis              -9                   -9
    9  airstn              x                    A
    10 towndis             -9                   1
       grveg               COOL FIELD/WOODS     COOL CROPS
        An indication of vegetation, from a gridded dataset. For example,
        'TROPICAL DRY FOR'.
    G  popcss              A                    C
        Population class based on satellite lights (GHCN value).
    U  us_light            1                    3
        Urban/Rural flag based on satellite lights for US stations
        (' ' for non-US stations).  '1' is dark, '3' is bright.
    11 global_light        0                    125
	Global satellite nighttime light value.  Range 0-186 (at
	least).

    The last two fields (us_light and global_light) are specific to the
    version of the v2.inv file supplied by GISS with GISTEMP.
    """

    # Do not supply both arguments!
    assert not (file and path)

    assert format in ('v2', 'v3', 'ushcnv2')
    if path:
        try:
            file = open(path)
        except IOError:
            warnings.warn("Could not load %s metadata file: %s" %
              (format, path))
            return {}
    assert file

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
    # documentation (even for the USHCN v2 and GHCN v2 fields, which
    # have slightly different names in their respective documentation)
    # except for:
    # uid (GHCN: ID), lat (GHCN: latitude), lon (GHCN: longitude),
    # us_light (GISTEMP specific field for nighttime satellite
    # brightness over the US, see Hansen et al 2001), global_light
    # (GISTEMP specific field for global nighttime satellite
    # brightness).
    # 
    # GISTEMP only uses some of the fields: uid, lat, lon, popcls (for
    # old-school rural/urban designation), us_light (for old-school
    # rural/urban designation in the US), global_light (for
    # 2010-style rural/urban designation).

    v2fields = dict(
        uid=         (0,   11,  str),
        name=        (12,  42,  str),
        lat=         (43,  49,  float),
        lon=         (50,  57,  float),
        stelev=      (58,  62,  int),
        grelev=      (62,  67,  blank_int),
        popcls=      (67,  68,  str),
        popsiz=      (68,  73,  blank_int),
        topo=        (73,  75,  str),
        stveg=       (75,  77,  str),
        stloc=       (77,  79,  str),
        ocndis=      (79,  81,  blank_int),
        airstn=      (81,  82,  str),
        towndis=     (82,  84,  blank_int),
        grveg=       (84,  100, str),
        popcss=      (100, 101, str),
        us_light=    (101, 102, str),           # GISTEMP only
        global_light=(102, 106, blank_int),     # GISTEMP only
    )

    # the GHCNv3 metadata file provided by GISS, which is restructured
    # from the GHCN-provided one to look like the GHCNv2 one above,
    # but has slightly different final fields.
    
    v3fields = dict(
        uid=         (0,   11,  str),
        name=        (12,  42,  str),
        lat=         (43,  49,  float),
        lon=         (50,  57,  float),
        stelev=      (58,  62,  int),
        grelev=      (62,  67,  blank_int),
        popcls=      (67,  68,  str),
        popsiz=      (68,  73,  blank_int),
        topo=        (73,  75,  str),
        stveg=       (75,  77,  str),
        stloc=       (77,  79,  str),
        ocndis=      (79,  81,  blank_int),
        airstn=      (81,  82,  str),
        towndis=     (82,  84,  blank_int),
        grveg=       (84,  100, str),
        popcss=      (100, 101, str),
        global_light=(101, 106, blank_int),   # GISTEMP only
        berkeley=    (106, 109, str),         # GISTEMP only; comment suggests derived from Berkeley Earth.
    )
    
    # See ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3/README for format
    # of GHCN's original metadata file.
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

    ushcnv2fields = dict(
        uid=     (0,  6, str),
        lat=     (7, 15, float),
        lon=     (16,25, float),
        stelev=  (26,32, float),
        us_state=(33,35, str),
        name=    (36,66, str),
    )
        
    if 'v2' == format:
        fields = v2fields
    elif 'v3' == format:
        fields = v3_ghcn_fields
    elif 'ushcnv2' == format:
        fields = ushcnv2fields

    result = {}
    for line in file:
        d = dict((field, convert(line[a:b]))
                  for field, (a,b,convert) in fields.items())
        result[d['uid']] = giss_data.Station(**d)

    return result

def augmented_station_metadata(path=None, file=None, format='v2'):
    """Reads station metadata just like station_metadata() but
    additionally augments records with metadata obtained from another 
    file, specified by parameters.augment_metadata.
    """

    meta = station_metadata(path=path, file=file, format=format)
    augments = parameters.augment_metadata
    if augments:
        path,columns = augments.split('=')
        columns = columns.split(',')
        assert 'uid' in columns
        for row in open(path):
            row = row.strip().split(',')
            d = dict(zip(columns,row))
            # Convert things that look like numbers, to numbers.
            # (except for uid, which is always a string)
            for k,v in d.items():
                if k == 'uid':
                    continue
                try:
                    v = float(v)
                except ValueError:
                    pass
                d[k] = v
            uid = d['uid']
            if uid in meta:
                meta[uid].__dict__.update(d)
    return meta



def read_generic(name):
    """Reads a "generic" source.  *name* should be a prefix, generally
    ending in '.v2', example: "ca.v2".  In the input directory the data
    file "foo.v2.mean" will be opened (where *name* is "foo.v2") and
    records from it will be yielded.  If the file "foo.v2.inv" is
    present it will be used as metadata (as well as the normal v2.inv
    file, meaning that any records in "foo.v2.mean" that have GHCN
    identifiers do not need new metadata).  If the file "foo.tbl" is
    present, it will be used to rename the station identifiers.
    """

    f = open(os.path.join('input', name+'.mean'))

    # Read the metadata from the v3.inv file, then merge in foo.v2.inv
    # file if present.
    meta = v3meta()
    try:
        m = open(os.path.join('input', name+'.inv'))
        print "  Reading metadata from %s" % m.name
    except:
        m = None
    if m:
        extrameta = augmented_station_metadata(file=m, format='v2')
        meta.update(extrameta)

    # Read the data.
    stations = GHCNV2Reader(file=f, meta=meta,
        year_min=code.giss_data.BASE_YEAR)

    # Convert IDs if a .tbl file is present.
    try:
        tbl = open(os.path.join('input', name.replace('v2', 'tbl')))
        print "  Translating IDs using %s" % tbl.name
    except:
        tbl = None
    if tbl:
        return convert_generic_id(stations, tbl, meta)

    return stations

def convert_generic_id(stream, tblfile, meta=None):
    """Convert identifiers of the records in *stream* using the contents
    of the table *tblfile*.  *tblfile* should have one line,
    "oldid newid", for each identifier mapping.  If a record's
    identifier does not appear in the table, it will be passed through
    unchanged.  Any record that gets a new identifier will have its
    '.station' member set to the metadata entry from the *meta* dict (if
    it is specified.
    """

    table = dict(row.split() for row in tblfile)
    meta = meta or {}

    for record in stream:
        if record.uid in table:
            record.uid = table[record.uid]
            id11 = record.uid[:11]
            if id11 in meta:
                record.station = meta[id11]
        yield record


def read_float(s):
    """Returns the float converted from the argument string.
    If float conversion fails, returns MISSING.
    """

    try:
        return float(s)
    except:
        return giss_data.MISSING

_v3meta = None
def v3meta():
    """Return the GHCN v3 metadata.  Loading it (from the modified
    version of the file supplied by GISS) if necessary.
    """

    # It's important that this file be opened lazily, and not at module
    # load time (if "input/" hasn't been populated yet, it won't be
    # found).
    # See http://code.google.com/p/ccc-gistemp/issues/detail?id=88

    global _v3meta

    v3inv = os.path.join('input', 'v3.inv')
    if not _v3meta:
        _v3meta = augmented_station_metadata(v3inv, format='v3')
    return _v3meta
