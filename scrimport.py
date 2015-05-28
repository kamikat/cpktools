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

p = re.compile(r"(0x[0-9A-Fa-f]{10})-(0x[0-9A-Fa-f]{10})\((0x[0-9A-Fa-f]{4})\)\t(.*)$")

def unpack_line(line):
    return tuple(filter(None, p.split(line)))

raw = map(lambda (x): x.strip('\r\n'), open(args.text, 'rb').read().decode('utf-8-sig').split('\n'))
txt = sorted(filter(lambda (x): not x.startswith('#') and not len(x) == 0, raw))

codetable = {}

if args.codefile:
    with open(args.codefile, 'r') as codefile:
        while True:
            line = codefile.readline().strip('\r\n')
            if len(line):
                code, character = line.decode('utf-8').split('=', 1)
                codetable[character] = code.decode('hex')
            else:
                break

with open(args.output, 'wb') as output:

    srcptr = 0

    for line in txt:
        try:
            (start, end, length, text) = unpack_line(line)
        except Exception as e:
            print '[ERROR] reading line %d: ' % (raw.index(line) + 1), e
            print '[DEBUG] rawdata: ', (line,)
            print '[DEBUG] matches: ', unpack_line(line)
            continue

        if args.codefile:
            data = ''
            for character in text:
                if codetable.has_key(character):
                    data += codetable[character]
                else:
                    data = ''
                    print '[WARNING] Missing character', character.encode('utf-8'), 'at', line
                    break
        else:
            data = text.encode('shift-jis')

        if len(data) == 0:
            print '[WARNING] Skipped 0x%s-0x%s' % (start, end)
            continue

        output.write(src[srcptr:int(start, 0)])
        output.write(struct.pack("<h", len(data) + 4))
        output.write(data)
        output.write('\x00\x00')

        srcptr = int(end, 0)

    output.write(src[srcptr:])

exit(0)
