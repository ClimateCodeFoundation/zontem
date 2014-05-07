#!/usr/bin/env python
# $URL$
# $Rev$
#
# correlation.py
#
# Calculate correlation coefficient.

from __future__ import division
import math

def pearson(X, Y):
    # See http://en.wikipedia.org/wiki/Correlation_and_dependence

    n = len(X)
    assert len(Y) == n

    xbar = mean(X)
    ybar = mean(Y)

    numerator = sum(((x-xbar)*(y-ybar) for x,y in zip(X,Y)))

    rank = numerator/((n-1)*sstddev(X)*sstddev(Y))
    return rank

def mean(X):
    return sum(X)/len(X)

def sstddev(X):
    """Sample standard deviation."""

    xbar = mean(X)
    return math.sqrt(sum((x-xbar)**2 for x in X) / (len(X)-1))

def main():
    import random
    print pearson(range(9), range(9))
    print pearson([random.random() for _ in range(99)],
      [random.random() for _ in range(99)])

if __name__ == '__main__':
    main()
