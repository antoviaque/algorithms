#!/usr/bin/python
# -*- coding: utf-8 -*-

import lempelziv, sys

# Main ##################################

filename = sys.argv[1]

with open(filename, 'r') as f:
    text = f.read()

data = lempelziv.compress(text)

with open("%s.lz" % filename, 'w+') as f:
    f.write(data)



