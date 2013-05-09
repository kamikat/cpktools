#!/usr/bin/env python

import struct
import re

src = open('scr.bin', 'rb').read()

p = re.compile(r"(0x[0-9A-Fa-f]{10})-(0x[0-9A-Fa-f]{10})\((0x[0-9A-Fa-f]{4})\)\t(.*)\r$")

def unpack_line(line):
    return tuple(filter(None, p.split(line)))

txt = map(
        lambda (x): x.lstrip(), 
        open('scr.utf8.txt', 'rb').read().split('\n')
        )

output = open('scr.packed.bin', 'wb')

srcptr = 0

for i in xrange(len(txt) - 1):

    if txt[i].startswith("#"):
        continue
    
    (start, end, length, text) = unpack_line(txt[i])

    output.write(src[srcptr:int(start, 0)])

    data = text.decode('utf-8').encode('shift-jis')

    output.write(struct.pack("<h", len(data) + 4))
    output.write(data)
    output.write('\x00\x00')

    srcptr = int(end, 0)

output.write(src[srcptr:])

output.close()
