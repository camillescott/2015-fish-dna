from __future__ import print_function
import argparse
import os
import sys
import csv
import khmer
import threading
import textwrap
from khmer import khmer_args
from khmer.khmer_args import (build_counting_args, add_threading_args,
                              report_on_config, info, calculate_graphsize,
                              sanitize_help)
import screed

def iterkmers(seq, K):

    for i in xrange(len(seq) - K + 1):
        yield seq[i:i+K]

def main():

    parser = build_counting_args()
    parser.add_argument('--min-abundance', default=50, type=int)
    parser.add_argument('input_files', nargs='+')
    parser.add_argument('-o', '--out', type=argparse.FileType('wb'), default=sys.stdout)
    args = parser.parse_args()

    countgraph = khmer_args.create_countgraph(args, multiplier=1.1)

    count = 0
    for fn in args.input_files:
        short = os.path.basename(fn)
        for n, record in enumerate(screed.open(fn)):
            if n % 100000 == 0:
                print('Processed {n} reads...'.format(n=n), file=sys.stderr)
            countgraph.consume(record.sequence)
            if countgraph.median_at_least(record.sequence, args.min_abundance):
                args.out.write('>{fn}:{name}:{c}\n{seq}\n'.format(fn=short, c=count, name=record.name, seq=record.sequence))
                count += 1

if __name__ == '__main__':
    main()
