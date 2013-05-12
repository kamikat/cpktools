#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description='Plant text back to original file')
parser.add_argument('source', help='original scenario file')
parser.add_argument('inputs', nargs='+', help='text file(s) with tag')
parser.add_argument('-o', '--output', default='out.bin',
        help='output destination') 
args = parser.parse_args()

import struct
import re

src = open(args.source, 'rb').read()

p = re.compile(r"(0x[0-9A-Fa-f]{10})-(0x[0-9A-Fa-f]{10})\((0x[0-9A-Fa-f]{4})\)\t(.*)\r$")

def unpack_line(line):
    return tuple(filter(None, p.split(line)))

txt = sorted(
        filter(lambda (x): not x.startswith('#') and not len(x) == 0,
            map(lambda (x): x.lstrip(), 
                reduce(lambda (a, b): a + b, 
                    map(lambda (f): open(f, 'rb').read().split('\n'), 
                        args.inputs
                        )
                    )
                )
            )
        )

with open(args.output, 'wb') as output:

    srcptr = 0

    for line in txt:

        (start, end, length, text) = unpack_line(line)

        output.write(src[srcptr:int(start, 0)])

        data = text.decode('utf-8').encode('shift-jis')

        output.write(struct.pack("<h", len(data) + 4))
        output.write(data)
        output.write('\x00\x00')

        srcptr = int(end, 0)

    output.write(src[srcptr:])

exit(0)
