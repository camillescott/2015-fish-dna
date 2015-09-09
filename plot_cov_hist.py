#!/usr/bin/env python

import matplotlib as mpl
mpl.use('Agg')
from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns

from figmanager import FigManager

import argparse
import os

mpl_params = {'figure.autolayout': True,
               'axes.titlesize': 24,
               'axes.labelsize': 16,
               'ytick.labelsize': 14,
               'xtick.labelsize': 14
               }
sns.set(style="white", palette="Paired", rc=mpl_params)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--hist-file')
    parser.add_argument('-o', '--output-prefix')
    parser.add_argument('--format', nargs='+', default=['pdf'])
    parser.add_argument('--title', default='Coverage Histogram')
    args = parser.parse_args()

    df = pd.read_csv(args.hist_file)
    if not args.output_prefix:
        args.output_prefix = os.path.basename(args.hist_file)

    with FigManager(show=False, save=args.output_prefix, exts=args.format) as (fig, ax):
        ax.plot(df['abundance'], df['count'])
        ax.set_title(args.title)
        ax.set_ylabel('Count')
        ax.set_xlabel('Abundance')

if __name__ == '__main__':
    main()
