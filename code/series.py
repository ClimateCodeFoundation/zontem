#!/usr/bin/env python
#
# series.py
#
# Nick Barnes, Ravenbrook Limited, 2010-03-08

import itertools

from data import valid, invalid, MISSING

"""
Shared series-processing code in the GISTEMP algorithm.
"""


def combine(composite, weight, new, new_weight, min_overlap):
    """Run the GISTEMP combining algorithm.  This combines the data
    in the *new* array into the *composite* array.  *new* has weight
    *new_weight*; *composite* has weights in the *weight* array.

    *new_weight* can be either a constant or an array of weights for
    each datum in *new*.

    For each of the 12 months of the year, track is kept of how many
    new data are combined.  This list of 12 elements is returned.

    Each month of the year is considered separately.  For the set of
    times where both *composite* and *new* have data the mean difference
    (a bias) is computed.  If there are fewer than *min_overlap* years
    in common, the data (for that month of the year) are not combined.
    The bias is subtracted from the *new* record and it is point-wise
    combined into *composite* according to the weight *new_weight* and
    the existing weights for *composite*.
    """

    new_weight = ensure_array(weight, new_weight)

    # A count (of combined data) for each month.
    data_combined = [0] * 12
    for m in range(12):
        bias, overlap = bias_overlap(composite[m::12], new[m::12])
        if overlap < min_overlap:
            continue

        # Update period of valid data, composite and weights.
        for i in range(m, len(new), 12):
            if invalid(new[i]):
                continue
            new_month_weight = weight[i] + new_weight[i]
            composite[i] = (weight[i]*composite[i]
                          + new_weight[i]*(new[i]+bias))/new_month_weight
            weight[i] = new_month_weight
            data_combined[m] += 1
    return data_combined

def bias_overlap(ps, qs):
    """Compute the bias between series *ps* and *qs* (positive
    when *ps* is on average bigger than *qs*).

    Returns a (bias, overlap) pair where overlap is the number
    of elements for which both *ps* and *qs* are valid.
    """

    # Sum of the data in each of *ps* and *qs*.
    sum_p = 0.0
    sum_q = 0.0
    # Number of elements where both *ps* and *qs* are valid.
    overlap = 0
    for p,q in itertools.izip(ps, qs):
        if invalid(p) or invalid(q):
            continue
        overlap += 1
        sum_p += p
        sum_q += q

    if overlap == 0:
        bias = None
    else:
        bias = (sum_p-sum_q)/overlap
    return (bias, overlap)

def ensure_array(exemplar, item):
    """Coerces *item* to be an array (linear sequence); if *item* is
    already an array it is returned unchanged.  Otherwise, an array of
    the same length as exemplar is created which contains *item* at
    every index.  The fresh array is returned.
    """

    try:
        item[0]
        return item
    except TypeError:
        return (item,)*len(exemplar)

def anomalize(data, reference_period=None, base_year=-9999):
    """Turn the series *data* into anomalies, based on monthly
    averages over the *reference_period*, for example (1951, 1980).
    *base_year* is the first year of the series.  If *reference_period*
    is None then the averages are computed over the whole series.
    Similarly, If any month has no data in the reference period,
    the average for that month is computed over the whole series.

    The *data* sequence is mutated.
    """

    means, anoms = monthly_anomalies(data, reference_period, base_year)
    # Each of the elements in *anoms* are the anomalies for one of the
    # months of the year (for example, January).  We need to splice each
    # month back into a single linear series.
    for m in range(12):
        data[m::12] = anoms[m]

def valid_mean(seq, min=1):
    """Takes a sequence, *seq*, and computes the mean of the valid
    items (using the valid() function).  If there are fewer than *min*
    valid items, the mean is MISSING."""

    count = 0
    sum = 0.0
    for x in seq:
        if valid(x):
            sum += x
            count += 1
    if count >= min:
        return sum/float(count)
    else:
        return MISSING

def monthly_anomalies(data, reference_period=None, base_year=-9999):
    """Calculate monthly anomalies, by subtracting from every datum
    the mean for its month.  A pair of (monthly_mean, monthly_anom) is
    returned.  *monthly_mean* is a 12-long sequence giving the mean for
    each of the 12 months; *monthly_anom* is a 12-long sequence giving
    the anomalized series for each of the 12 months.

    If *reference_period* is supplied then it should be a pair (*first*,
    *last*) and the mean for a month is taken over the period (an
    example would be reference_period=(1951,1980)).  *base_year*
    specifies the first year of the data.
    
    The input data is a flat sequence, one datum per month.
    Effectively the data changes shape as it passes through this
    function.
    """

    years = len(data) // 12
    if reference_period:
        base = reference_period[0] - base_year
        limit = reference_period[1] - base_year + 1
    else:
        # Setting base, limit to (0,0) is a bit of a hack, but it
        # does work.
        base = 0
        limit = 0
    monthly_mean = []
    monthly_anom = []
    for m in range(12):
        row = data[m::12]
        mean = valid_mean(row[base:limit])
        if invalid(mean):
            # Fall back to using entire period
            mean = valid_mean(row)
        monthly_mean.append(mean)
        if valid(mean):
            def asanom(datum):
                """Convert a single datum to anomaly."""
                if valid(datum):
                    return datum - mean
                return MISSING
            monthly_anom.append(map(asanom, row))
        else:
            monthly_anom.append([MISSING]*years)
    return monthly_mean, monthly_anom

