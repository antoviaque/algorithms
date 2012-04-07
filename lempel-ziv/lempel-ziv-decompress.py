#!/usr/bin/python
# -*- coding: utf-8 -*-

import lempelziv, sys

# Main ##################################

filename = sys.argv[1]

with open("%s" % filename) as f:
    data = f.read()

text = lempelziv.decompress(data)

with open("%s.uncompressed" % filename, 'w+') as f:
    f.write(text)



