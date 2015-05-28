#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description='Plant text back to original file')
parser.add_argument('source', help='original scenario file')
parser.add_argument('text', help='text file with tags')
parser.add_argument('-o', '--output', default='out.bin',
        help='output destination')
parser.add_argument('-c', '--codefile', help='code file')
parser.add_argument('-i', '--inplace', action='store_true', help='enable in-place mode')
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

def encode(text, line):
    if args.codefile:
        data = ''
        for character in text:
            if codetable.has_key(character):
                data += codetable[character]
            else:
                print '[WARNING] Missing character', character.encode('utf-8'), 'at', line
                return None
        return data
    else:
        return text.encode('shift-jis')

with open(args.output, 'wb') as output:

    srcptr = 0

    for line in txt:
        try:
            (start, end, length, text) = unpack_line(line)
        except Exception as e:
            print '[ERROR] Reading line %d: ' % (raw.index(line) + 1), e
            print '[ERROR] Rawdata: ', (line,)
            print '[ERROR] Matches: ', unpack_line(line)
            continue

        encoded = encode(text, line)

        if not encoded:
            print '[WARNING] Skipped 0x%s-0x%s' % (start, end)
            continue

        data = encoded

        if args.inplace:
            text_length = int(length, 0) - 4
            if len(data) > text_length:
                print '[EXCCEED] %4d/%-4d :: %s' % (len(data), text_length, line.encode('utf-8'))
                data = data[:text_length]
            # append tail padding
            if len(data) < text_length:
                data += '\x00' * (text_length - len(data))
            assert len(data) == text_length

        # handle duplicate lines
        if srcptr == int(end, 0):
            continue

        assert srcptr <= int(start, 0)

        output.write(src[srcptr:int(start, 0)])
        output.write(struct.pack("<h", len(data) + 4))
        output.write(data)
        output.write('\x00\x00')

        srcptr = int(end, 0)

    output.write(src[srcptr:])

exit(0)
