#!/usr/bin/env python

"""Classes for GISTEMP data.

Primarily, the classes herein support monthly temperature series.
Typically these are either for stations (station records) or subboxes
(subbox series).  In either case the same class is used, `Series`,
differing in what keyword arguments are supplied.

station records
    Stores a set of monthly averages associated with a particular monitoring
    `Station`.

subbox series
    Stores monthly averages for a subbox, typically synthesized by
    combining several station records together.

Both types of record can be grouped in collections, often (in the original
GISTEMP code) in files. Collections of records have associated metadata,
the `StationMetaData` and `SubboxMetaData` classes.

"""
__docformat__ = "restructuredtext"

import sys
# http://docs.python.org/release/2.4.4/lib/warning-functions.html
import warnings

#: The base year for time series data. Data before this time is not
#: used in calculations.
BASE_YEAR = 1880

#: The value that is used to indicate a bad or missing data point.
MISSING = 9999.0

def invalid(v):
    return v == MISSING

def valid(v):
    return not invalid(v)


_v2_sources = None


class Station(object):
    """A station's metadata.

    This holds the information about a single (weather monitoring) station. Not
    all the attributes are used by the CCC code.  For a list of
    attributes and documentation, see the io.station_metadata() function.
    """
    def __init__(self, **values):
        self.__dict__.update(values)

    def __repr__(self):
        return "Station(%r)" % self.__dict__

def clear_cache(func):
    """A decorator, for `Series` methods that change the data.

    Any method that changes the underlying data series in a `Series`
    instance must clear the cached values used for some properties.
    This decorator takes care of this chore.

    """
    def f(self, *args, **kwargs):
        self._good_count = None
        return func(self, *args, **kwargs)

    return f


class StationMetaData(object):
    """The metadata for a set of station records.

    The keyword arguments for the constructor are entirely arbitrary.
    The constructor accepts any keyword arguments and merely acts as a
    repository.  By convention the keyword arguments are:

    :Ivar mo1:
        The number of months covered in the entire data set.
    :Ivar kq:
        The KQ quantity from the header record.
    :Ivar mavg:
        A code indicating the length of time each average value represents. The
        only supported by the CCC code is '6', which indicates that each entry
        is a monthly average. The effect of this having a different value is
        undefined.
    :Ivar monm:
        Maximum length of any time record.
    :Ivar monm4:
        This is the size of this record when written to a GISS Fortran
        unformatted file.

        TODO: This can probably be ditched and calculated as required
        in I/O code.
    :Ivar yrbeg:
        The year of first data.
    :Ivar missing_flag:
        The value used to indicate a missing value in the `series`. This is
        often referred to in other code as variously bad, BAD, XBAD.

        This should become unimportant over time in the CCC code, which should
        stick to always using the `MISSING` value.
    :Ivar precipitation_flag:
        Probably defines a special value that serves a similar purppose to
        the `missing_flag`. This does not seem to be used by any CCC code.
    :Ivar mlast:
        TODO
    :Ivar title:
        A title for this set of station records.
    """
    def __init__(self, **k):
        self.__dict__ = k

    def __repr__(self):
        return 'StationMetadata(%r)' % self.__dict__


# TODO: Needs some review. Among things to think about:
#
# 1. Might it be seen as too complicated? It is complicated for a reason; to
#    make the code that manipulates temperature series more readable.
# 2. Should we use properties or convert the properties to methods?
# 3. Some of the names are open to improvement.
class Series(object):
    """Monthly temperature Series.

    An instance contains a series of monthly data (in ccc-gistemp
    the data are average monthly temperature values in degrees
    Celsius), accessible via the `series` property.  This property
    should **always** be treated as read-only; the effect of modifying
    elements is undefined.

    The series coveres the months from `first_month` to `last_month` month
    inclusive. Months are counted from a non-existant year zero. So January,
    1 AD has a month number of 13, February is 14, etc.

    The GISTEMP/CCC code only uses data that starts from `BASE_YEAR` (1880).
    Some code works on data series that start from this base year. So it is
    convenient to be able to work in terms of years and months relative to this
    base year. There are a number of properties with names that start with
    `rel_` that provide values using this alternative reference.

    Note that most of the series metadata is provided by properties, which
    are effectively read-only. All the instance variables should also be
    treated as read-only and you should only set values in the data series
    using the provided methods.

    There are no subclasses of this class.  Some instances represent
    station records, other instances represent subbox series.

    For station records there can be multiple series for a single `Station`.
    The `station` property provides the associated `Station` instance.
    For a given station the different series are called "duplicates" in
    GHCN terminology; they have a 12-digit uid that is made up of an
    11-digit station identifier and a single extra digit to distinguish
    each of the station's series.

    Generally a station record will have its uid supplied as a keyword
    argument to the constructor (accessing the `station` property relies
    on this):

    :Ivar uid:
        An integer that acts as a unique ID for the time series. This
        is generally a 12-digit identifier taken from the GHCN file; the
        first 11 digits comprise an identifier for the station.
	The last digit distinguishes this series from other series
	from the same station.

    A first year can be supplied to the constructor which will base the
    series at that year:

    :Ivar first_year:
        Set the first year of the series.  Data that are
        subsequently added using add_year will be ignored if they
        precede first_year (a typical use is to set first_year to 1880
        for all records, ensuring that they all start at the same year).

    When used to hold a series for a subbox, for example a record of data
    as stored in the ``input/SBBX.HadR2`` file, then the following
    keyword arguments are traditionally supplied to the constructor:

    :Ivar lat_S, lat_N, lon_W, lon_E:
        Coordinates describing the box's area.
    :Ivar stations:
        The number of stations that contributed to this sub-box.
    :Ivar station_months:
        The number of months that contributed to this sub-box.
    :Ivar d:
        Characteristic distance to station closest to centre.

    """
    def __init__(self, **k):
        self._first_month = sys.maxint
        self._series = []
        self._good_count = None
        self.ann_anoms = []
        series = None
        if 'first_year' in k:
            first_year = k['first_year']
            if first_year:
                self._first_month = first_year*12 + 1
            del k['first_year']
        self.__dict__.update(k)

    def __repr__(self):
        # Assume it is a station record with a uid.
        return "Series(uid=%r)" % self.uid

    @property
    def series(self):
        """The series of values (conventionally in degrees Celsius)."""
        return self._series

    def __len__(self):
        """The length of the series."""
        return len(self._series)

    @property
    def first_month(self):
        """The number of the first month in the data series.

        This number is counted from January (being 1) in a non-existant
	year zero. The property `last_month` provides the other end
	of the inclusive range of months held in the `series`.

        The `series` contains `last_month` - `first_month` + 1 entries.

        """
        return self._first_month

    @property
    def last_month(self):
        """The number of the last month in the data series.

        The `series` contains ``last_month`` - `first_month` + 1 entries.
        See `first_month` for details of how months are counted.

        """
        return (self.first_month + len(self._series) - 1)

    @property
    def first_year(self):
        """The year of the first value in the series."""
        return (self.first_month - 1) // 12

    @property
    def last_year(self):
        """The year of the last value in the series."""
        return (self.last_month - 1) // 12

    @property
    def good_count(self):
        """The number of good values in the data."""
        if self._good_count is None:
            bad_count = 0
            for v in self._series:
                bad_count += invalid(v)
            self._good_count = len(self._series) - bad_count
        return self._good_count

    def first_valid_year(self):
        """The first calendar year with any valid data."""
        return (self.first_valid_month() - 1) // 12

    def last_valid_year(self):
        """The last calendar year with any valid data."""
        return (self.last_valid_month() - 1) // 12

    def first_valid_month(self):
        """The first month with any valid data.  Returned as a 1-based
        index (where January of year 0 is 1).
        """
        index = (i for i,x in enumerate(self.series) if x != MISSING)
        try:
            first = index.next()
        except StopIteration:
            # No valid data.  Return a large number.
            return 9999*12
        return first + self.first_month

    def last_valid_month(self):
        """The last month with any valid data.  Returned as a 1-based
        index (where January of year 0 is 1).
        """
        index = (i for i,x in reversed(list(enumerate(self.series)))
          if x != MISSING)
        try:
            last = index.next()
        except StopIteration:
            # No valid data.  Return a small number.
            return 1
        return last + self.first_month

    def get_monthly_valid_counts(self):
        """Get number of good values for each month.

        :Return:
            A list of 12 entries. Entry zero is the number of good entries
            for January, entry 1 for February, etc.

        """
        monthly_valid = [0] * 12
        for i, v in enumerate(self._series):
            monthly_valid[(self.first_month + i - 1) % 12] += valid(v)
        return monthly_valid

    # Year's worth of missing data
    missing_year = [MISSING]*12

    def has_data_for_year(self, year):
        return self.get_a_year(year) != self.missing_year

    def _get_a_month(self, month):
        """Get the value for a single month."""
        idx = month - self.first_month
        if idx < 0:
            return MISSING
        try:
            return self.series[month - self.first_month]
        except IndexError:
            return MISSING

    # If you are tempted to optimise the following, like drj was, note
    # that it is a little tricky to cope with: years that entirely
    # precede the first year; and, an initial partial year when the
    # series does not begin in January.
    def get_a_year(self, year):
        """Get the time series data for a year."""
        start_month = year * 12 + 1
        return [self._get_a_month(m)
                for m in range(start_month, start_month + 12)]

    @property
    def station_uid(self):
        """The unique ID of the corresponding station."""
        return self.uid[:11]

    # Mutators below here

    def add_year(self, year, data):
        """Add a year's worth of data.  *data* should be a sequence of
        length 12.  Years must be added in increasing order (though the
        sequence is permitted to have gaps in, and these will be filled
        with MISSING).
        """

        if self.first_month == sys.maxint:
            self._first_month = year * 12 + 1
        else:
            # We have data already, so we may need to pad with missing months
            # Note: This assumes the series is a whole number of years.
            gap = year - self.last_year - 1
            if gap > 0:
                self._series.extend([MISSING] * (gap * 12))
        assert self.first_month % 12 == 1
        if year < self.first_year:
            # Ignore years before the first year.  Previously this case
            # was extremely buggy.
            return
        assert year == self.last_year + 1
         
        self._series.extend(data)
