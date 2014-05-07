#!/usr/bin/env python
# $URL$
# $Rev$
#
# plotdist.py
#
# Distance/Correlation plot

def plot(input='distances'):
    # Pixels per kilometre
    xs = 0.2
    # Unitless Y-scale
    ys = 500
    # In units of original data
    rangex = (0,5000)
    # In units of original data
    rangey = (-0.4, 1.0)
    # Small margin at top
    ymargin = 6

    f = open(input)
    print """
<svg
      xmlns="http://www.w3.org/2000/svg"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      version="1.1">
<defs>
  <style type="text/css">
     path { stroke-width: 1; fill: none; stroke: blue }
     g#grid path { stroke: pink }
  </style>
</defs>
"""
    print "<g id='grid'>"
    yheight = (rangey[1] - rangey[0]) * ys
    ytop = ymargin
    for x in range(0,5001,1000):
        x = x*xs
        print "<path d='M%.1f %.1fl0 %.1f' />" % (x, ytop, yheight)
    xleft = 0
    xwidth = (rangex[1] - rangex[0]) * xs
    for y in range(-4,11):
        y *= 0.1
        y = rangey[1] - y
        y *= ys
        y += ymargin
        print "<path d='M%.1f %.1fl%.1f 0' />" % (xleft, y, xwidth)
    print "</g>"
    for row in f:
        _,_,corr,_,_,d,u,v = row.split()
        corr,d,u,v = map(float, [corr,d,u,v])
        x = d*xs
        y = rangey[1] - corr
        y *= ys
        y += ymargin
        print "<path d='M%.1f %.1fl%.1f %.1f' />" % (
          x, y, u*10, v*10)

    print "</svg>"

def main(argv=None):
    import sys

    if argv is None:
        argv = sys.argv
    plot(*argv[1:])

if __name__ == '__main__':
    main()
