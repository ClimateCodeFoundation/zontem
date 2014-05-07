#!/usr/bin/env python
# $URL$
# $Rev$
#
# splitzon.py
#
# Split distance file by zone.

import math

def split(input='distances', n=20):
    out = [open('zondist%d' % i, 'w') for i in range(n)]
    for row in open(input):
        location = row.split()[3]
        lat = float(location[:6])
        z = math.sin(lat*math.pi/180.0)
        z = int(math.floor((z+1)*n/2.0))
        z = min(z, n-1)
        out[z].write(row)

    for f in out:
        f.close()

def main(argv=None):
    import sys
    if argv is None:
        argv = sys.argv

    split(*argv[1:])

if __name__ == '__main__':
    main()
