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

The most obvious competing analyses of global temperature change
are GISTEMP, CRUTEM4, NOAA (this is not an exhaustive list).

 - data sources. ZONTEM uses the GHCN-M product as its only data
   source. Other analyses use this supplemented with SCAR READER
   records, various priv comm records, or replace GHCN-M with a
   privately maintained database with similar coverage.

 - SSTs. Other analyses may have an optional procedure where Sea Surface
   Temperatures (SST) are used over the ocean. CRUTEM4 has a sister
   product, HadCRUT, that also incorporates SSTs. Whilst
   recognising that the Earth's surface is mostly ocean, ZONTEM does
   not incorporate SSTs.

 - gridding. Other analyses compute global temperature anomaly via a
   gridded product (the gridded product may be regarded as more
   essential than the global summary). ZONTEM dispenses with the grid,
   instead using a small number of zones (you could alternatively think
   of it as a 1x20 grid).
   
 - QC. Other analyses may have a QC step that rejects
   invalid station records. ZONTEM assumes that the input
   has been quality controlled.

 - inhomogeneity. Other analyses may have a step that adjusts
   or rejects inhomogeneous records. ZONTEM does not perform such
   a step (but it is possible to use the adjusted version of
   GHCN-M as input).
