#!/usr/bin/env python

import os
import re
import sys
import tarfile
import urllib2

class Error(Exception):
    """Some error."""

URL = 'http://www1.ncdc.noaa.gov/pub/data/ghcn/v3/ghcnm.tavg.latest.qca.tar.gz'
def fetch(url):
    basename = os.path.basename(url)
    output = os.path.join("input", basename)
    if os.path.exists(output):
        return output

    f = urllib2.urlopen(url)
    with open(output, 'wb') as o:
        while True:
            s = f.read(9999)
            sys.stderr.write(".")
            sys.stderr.flush()
            if not s:
                break
            o.write(s)
        sys.stderr.write("\n")
    return output

def unpack(targz):
    with tarfile.open(targz) as tar:
        for name in tar.getnames():
            if not re.match(r"((?![.][.])[.a-zA-Z0-9]+(/|$))+",
              name):
                raise Error(
                  "tar file contains filename {} and I don't like it".format(name))
        if all(os.path.exists(name) for name in tar.getnames()):
            return
        tar.extractall(path="input")

def main():
    filename = fetch(URL)
    unpack(filename)
    from code import zontem
    zontem.main(["zontem"])

if __name__ == '__main__':
    main()
