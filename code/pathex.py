# http://docs.python.org/release/2.4.4/lib/module-os.path.html
import os
import sys

my_path = os.path.abspath(__file__)
path = my_path
last_path = None
while last_path != path:
    last_path = path
    path = os.path.dirname(path)
    p = os.path.join(path, 'ccc-gistemp')
    if os.path.exists(p):
        sys.path.insert(0, p)
        # sys.path.insert(0, os.path.join(p, 'code'))
        # sys.path.insert(0, os.path.join(p, 'tool'))
