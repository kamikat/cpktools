#!/bin/sh

cat $1 | python -c 'import sys; sys.stdout.write(sys.stdin.read()[::-1])' | xxd -u > $2

# Reverse Bytes in $1, convert to hexdump and write to $2
