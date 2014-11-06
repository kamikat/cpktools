#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description='Plant text back to original file')
parser.add_argument('source', help='original scenario file')
parser.add_argument('text', help='text file with tags')
parser.add_argument('-o', '--output', default='out.bin',
        help='output destination')
parser.add_argument('-c', '--codefile', help='code file')
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
                open(args.text, 'rb').read().split('\n')
                )
            )
        )

codetable = {}

if args.codefile:
    with open(args.codefile, 'r') as codefile:
        while True:
            line = codefile.readline().strip('\r\n')
            if len(line):
                code, character = line.decode('utf-8').split('=', 1)
                codetable[character] = struct.pack('>H', int(code, 16))
            else:
                break

with open(args.output, 'wb') as output:

    srcptr = 0

    for line in txt:

        try:
            (start, end, length, text) = unpack_line(line)
        except:
            continue

        text = text.decode('utf-8')

        if args.codefile:
            data = ''
            for character in text:
                if codetable.has_key(character):
                    data += codetable[character]
                else:
                    print '[WARNING] Missing character', character.encode('utf-8'), 'at', line
                    continue
        else:
            data = text.encode('shift-jis')

        output.write(src[srcptr:int(start, 0)])
        output.write(struct.pack("<h", len(data) + 4))
        output.write(data)
        output.write('\x00\x00')

        srcptr = int(end, 0)

    output.write(src[srcptr:])

exit(0)
