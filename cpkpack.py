#!/usr/bin/env python

if __name__ == '__main__':

    import argparse
    from sys import stderr

    parser = argparse.ArgumentParser(description='Pack up a cpk archive')
    parser.add_argument('dir', help='Directory with content to pack up')
    parser.add_argument('-r', '--remake', 
            dest='cpk',
            help='Make a cpk file with the same XTOC as the cpk file given')
    args = parser.parse_args()

