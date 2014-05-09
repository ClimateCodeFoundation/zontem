#!/usr/bin/env python
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


import itertools
import warnings


# Clear Climate Code
import giss_data


#: Integer code used to indicate missing data.
#:
#: This is units of 0.1 celsius. This code is only used when
#: reading or writing input and working files.
MISSING = 9999


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
