ZONTEM
======

ZONTEM is a method for computing the change in global temperature over
the recent period (1880 CE to present) from published records of
monthly mean temperatures (GHCN-M V3).

Running ZONTEM
==============

```
cd code
# somehow get GHCN-M V3 into the input/ directory and unpack it
./zontem.py
```

Methodology
===========

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

