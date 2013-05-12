#!/bin/sh

cat $1 | python -c 'import sys; sys.stdout.write(sys.stdin.read()[::-1])' > $2

cat $2 | xxd -u > $3

# Reverse Bytes in $1 write to $2, convert to hexdump and write to $3
