#!/usr/bin/env python

import struct

data = open('scr.bin', 'rb').read()

output = open('.analyse.txt', 'w')

length = len(data)

counted = 0

for i in xrange(length - 2):
    val = struct.unpack("<h", data[i:i+2])[0]
    if val < 0:
        continue
    if val > length:
        continue
    if data[i+val-2:i+val] != '\x00\x00':
        continue
    try:
        strline = data[i+2:i+val-2].decode('shift-jis')
        for char in strline:
            if char < "\x1f":
               strline = None
        if not strline:
            continue
        counted += val
        if len(strline) > 0:
            print >>output, "0x%010X-0x%010X(0x%04X)\t%s\r" % \
                    (i, i + val, val, strline.encode('utf-8'))
    except:
        continue

print "Byte Coverage: %d/%d(%02d%%)" % (counted, length, counted * 100 / length)

output.close()
