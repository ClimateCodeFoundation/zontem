ZONTEM
======

ZONTEM is a method for computing the change in global temperature over
the recent period (1880 CE to present) from published records of
monthly mean temperatures (GHCN-M V3).

ZONTEM aims to be as simple as possible while still giving a
reasonable result.

Running ZONTEM
==============

```
# somehow get GHCN-M V3 into the input/ directory and unpack it
code/zontem.py
```

Method
======

The input is a number of records, each record being a
time series of monthly (air) temperature averages from a single
station.

The input records are distributed into N (=20 by default) zones
according to the latitude of the station. Each zone represents
the surface of the globe between two circles of latitude; each
zone covers an equal area.

All the station records in a zone are combined into one record by the
Reference Station Method described in [HANSEN1987].

All the zone records are combined into a single global record using the
same method.

The global record is converted to annual anomalies by first
converting to monthly anomalies and then averaging into years
where a year has all 12 monthly anomalies present. 

Comparison
==========

The most obvious competing data products are GISTEMP, CRUTEM4,
NOAA. Each of these compute global temperature anomaly via a
gridded product. ZONTEM dispenses with the grid, instead using a
small number of zones (you could alternatively think of it as a
1x20 grid). Each of these products has a QA step that rejects
invalid station records, and an adjustment to remove
inhomogeneities. While these may be important for producing
reasonable grid values, for a global analysis they have very
little effect. ZONTEM dispenses with these steps (but note that
the GHCN-M V3 dataset has been quality controlled). Each of the
competing products have different methods for weighting a
station when computing grid cells. ZONTEM dispenses with such
complications and weights all stations in a zone equally.

GISTEMP, and NOAA have an optional procedure where Sea Surface
Temperatures (SST) are used over the ocean. CRUTEM4 has a sister
product, HadCRUT, that also incorporates SSTs. ZONTEM does not
incorporate SSTs.
