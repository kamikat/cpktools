#!/usr/bin/env python

from struct import unpack
from array import array
import argparse

parser = argparse.ArgumentParser(description='crypt a cpk archive')
parser.add_argument('input', help='Input cpk file')
parser.add_argument('output', help='Output cpk file')
args = parser.parse_args()

infile = open(args.input, 'rb')

outfile = open(args.output, 'wb')

def known(header):
    if header.startswith('CRILAYLA'): return "CRILAYLA"
    if header.startswith('CRI'): return "CRI"
    if header.startswith('GIM.00.1PSP'): return "GIM"
    if header.startswith('1raw'): return "RAW"
    if header.startswith('\x80\x00\x00\x24\x03\x12\x04\x02\x00\x00\x56\x22'): return "80 00 00 24"
    if header.startswith('\x89PNG\x0D\x0A\x1A\x0A'): return "PNG"

def parseHeader(header):
    for i in xrange(4):
        if header[i*4 + 3] == '\x00':
            marker = header[:i*4 + 3].strip()
            size = unpack('<L', header[(i+1)*4: (i+2)*4])
            return (marker, size[0])

def chiper(data):
    c, m = (0x5f, 0x15)
    v = array('B', data)
    for i in xrange(len(v)):
        v[i] = v[i] ^ c & 0b11111111
        c = c * m & 0b11111111
    return v.tostring()

filecount = 0

while True:

    header = infile.read(0x10)

    if header == '': break;

    while header[0] == '\x00':
        outfile.write(header)
        header = infile.read(0x10)

    print "0x%010X Padding End" % (infile.tell() - 0x10)

    if header.startswith('\x80\x00\x00\x24\x03\x12\x04\x02\x00\x00\x56\x22'):

        outfile.write(header)
        print "0x%010X Found 80 00 00 24..." % (infile.tell())

        size = 0

        while True:
            data = infile.read(0x04)
            outfile.write(data)
            size += 4
            if data == '\x80\x01\x00\x0E':
                break;

        print "0x%010X Found 80 00 00 24 Data Block(0x%08X)" % (infile.tell(), size)

    elif header.startswith('MIG.00.1PSP\x00'):
        
        outfile.write(header)
        print "0x%010X Found Uncompressed GIM Header" % (infile.tell())

        reserved = infile.read(0x04)
        assert reserved == '\x02\x00\x00\x00'
        outfile.write(reserved)

        sizedata = infile.read(0x04)
        size, = unpack('<L', sizedata)
        outfile.write(sizedata)

        data = infile.read(size)
        outfile.write(data)

    elif header.startswith('\x89PNG\x0D\x0A\x1A\x0A'):

        outfile.write(header)
        print "0x%010X Found Uncompressed PNG Header" % (infile.tell())

        prvdata = ''
        while True:
            data = infile.read(0x10)
            outfile.write(data)
            if (prvdata + data.encode('hex')).find('49454e44ae426082') >= 0:
                break;
            else:
                prvdata = data.encode('hex')

    elif header.startswith('1raw'):

        outfile.write(header)
        print "0x%010X Found Uncompressed 1raw Header" % (infile.tell())

        while True:
            data = infile.read(0x10)
            if known(data):
                infile.seek(-0x10, 1)
                break;
            outfile.write(data)

    else:

        marker, size = parseHeader(header)

        outfile.write(header);
        if(marker.startswith('CRILAYLA')):
            print "0x%010X Found Header: %s %s" % (infile.tell(), marker[:8], marker[8:].encode('hex'))
        else:
            print "0x%010X Found Header: %s" % (infile.tell(), marker)

        data = infile.read(size)
        outfile.write(chiper(data))
        print "0x%010X Found Data Block(0x%08X)" % (infile.tell(), size)

        if marker.startswith("CRILAYLA"):
            size = 0x100
            fheader = infile.read(size)
            outfile.write(fheader)
            print "0x%010X Found Data Block - Header(0x%08X)" % (infile.tell(), size)

    if infile.tell() % 0x10 > 0:
        padding = infile.read(0x10 - infile.tell() % 0x10)
        outfile.write(padding)

    filecount += 1;

print "0x%010X File Processing Completed, %d files found." % (infile.tell(), filecount)

outfile.close();

infile.close();
