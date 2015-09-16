#!/usr/bin/env python

import matplotlib as mpl
mpl.use('Agg')
from matplotlib import pyplot as plt
import pandas as pd
from scipy import stats
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
sns.set(style="ticks", palette="Paired", rc=mpl_params)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--stats-file')
    parser.add_argument('-o', '--output-prefix')
    parser.add_argument('--format', nargs='+', default=['pdf'])
    args = parser.parse_args()

    df = pd.read_csv(args.stats_file, delimiter='\t')
    if not args.output_prefix:
        args.output_prefix = os.path.basename(os.path.dirname(args.stats_file).strip('/'))

    with FigManager(show=False, save=args.output_prefix + '.cov', exts=args.format) as (fig, ax):
        sns.distplot(df[df['short1_cov'] > 0]['short1_cov'], bins=50, kde=False)
        ax.set_title('{t} k-mer Coverage Histogram'.format(t=args.output_prefix))
        ax.set_ylabel('Count')
        ax.set_xlabel('k-mer Abundance')

    with FigManager(show=False, save=args.output_prefix + '.lgth', exts=args.format) as (fig, ax):
        sns.distplot(df[df['lgth'] > 0]['lgth'], bins=50, kde=False)
        ax.set_title('{t} k-mer Coverage Histogram'.format(t=args.output_prefix))
        ax.set_ylabel('Count')
        ax.set_xlabel('Length')

if __name__ == '__main__':
    main()
