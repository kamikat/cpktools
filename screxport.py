#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description='Scan file to find shift-jis string')
parser.add_argument('input', help='scenario file')
args = parser.parse_args()

import struct

data = open(args.input, 'rb').read()

length = len(data)

for i in xrange(length - 2):
    val = struct.unpack("<h", data[i:i+2])[0]
    if val < 0:
        continue
    if val > length:
        continue
    if val % 2 != 0:
        continue
    if data[i+val-2:i+val] != '\x00\x00':
        continue
    try:
        strline = data[i+2:i+val-2].decode('shift-jis')
        for char in strline:
            if char < "\x1f":
               strline = ""
        if len(strline) > 0:
            print "0x%010X-0x%010X(0x%04X)\t%s\r" % \
                    (i, i + val, val, strline.encode('utf-8'))
    except:
        continue

