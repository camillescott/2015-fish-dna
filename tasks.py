#!/usr/bin/env python
from __future__ import print_function

from itertools import izip
import json
import os
import pprint
import re
from shutil import rmtree
import shutil
import sys

from doit.tools import run_once, create_folder, title_with_actions
from doit.task import clean_targets, dict_to_task

import jinja2
import pandas as pd
import screed


def clean_folder(target):
    try:
        rmtree(target)
    except OSError:
        pass

seq_ext = re.compile(r'(.fasta)|(.fa)|(.fastq)|(.fq)')
def strip_seq_extension(fn):
    return seq_ext.split(fn)[0]

def create_task_object(task_dict_func):
    '''Wrapper to decorate functions returning pydoit
    Task dictionaries and have them return pydoit Task
    objects
    '''
    def d_to_t(*args, **kwargs):
        ret_dict = task_dict_func(*args, **kwargs)
        return dict_to_task(ret_dict)
    return d_to_t

@create_task_object
def build_velvet_task(file_list, template_fn, cur_time, velvet_cfg, pbs_cfg, label=''):

    if not label:
        label = 'velvet_' + '_'.join(file_list)

    with open(template_fn) as fp:
        template = jinja2.Template(fp.read())

    script_fn = cur_time + '-' + velvet_cfg['script_file']
    velvet_cfg['directory'] = cur_time + '-' + velvet_cfg['directory']

    velvet_cfg.update(pbs_cfg)
    def create_script(file_list, velvet_cfg, tpl):
        with open(script_fn, 'wb') as fp:
            pbs = tpl.render(file_list=file_list, **velvet_cfg)
            fp.write(pbs)

    #cmd = 'qsub {fn}'.format(fn=script_fn)

    return {'title': title_with_actions,
            'name': label,
            'actions': [(create_script, [file_list, velvet_cfg, template])],
            'file_dep': file_list + [template_fn],
            'targets': [script_fn],
            'clean': [clean_targets]}

@create_task_object
def format_abyss_task(input_filename, output_filename, label=''):

    import screed

    if not label:
        label = 'format_abyss_' + input_filename

    def format_abyss():
        with open(output_filename, 'wb') as fp:
            for n, record in enumerate(screed.open(input_filename)):
                if n % 2 == 0:
                    record.name = record.name + '/1'
                else:
                    record.name = record.name + '/2'
                fp.write('@{name}\n{seq}\n+\n{qual}\n'.format(name=record.name,
                         seq=record.sequence, qual=record.quality))
    
    return {'title': title_with_actions,
            'name': label,
            'actions': [(format_abyss, [])],
            'file_dep': [input_filename],
            'targets': [output_filename],
            'clean': [clean_targets]}

@create_task_object
def build_abyss_task(file_list, abyss_cfg, pbs_cfg, label=''):

    if not label:
        label = 'abyss_' + '_'.join(file_list)

    with open(abyss_cfg['template_file']) as fp:
        template = jinja2.Template(fp.read())

    abyss_cfg['name'] = CUR_TIME + '-' + abyss_cfg['name']
    abyss_cfg.update(pbs_cfg)

    script_fn = CUR_TIME + '-' + abyss_cfg['script_file']
    def create_script(file_list, abyss_cfg, tpl):
        with open(script_fn, 'wb') as fp:
            pbs = tpl.render(files=' '.join(file_list), **abyss_cfg)
            fp.write(pbs)

    #cmd = 'qsub {fn}'.format(fn=script_fn)

    return {'title': title_with_actions,
            'name': label,
            'actions': [(create_script, [file_list, abyss_cfg, template])],
            'file_dep': file_list + [abyss_cfg['template_file']],
            'targets': [script_fn],
            'clean': [clean_targets]}



@create_task_object
def diginorm_task(input_files, dg_cfg, label, ct_outfn=None):

    ksize = dg_cfg['ksize']
    table_size = dg_cfg['table_size']
    n_tables = dg_cfg['n_tables']
    coverage = dg_cfg['coverage']

    name = 'normalize_by_median_' + label
    report_fn = label + '.report.txt'

    inputs = ' '.join(input_files)
    ct_out_str = ''
    if ct_outfn is not None:
        ct_out_str = '-s ' + ct_outfn

    cmd = 'normalize-by-median.py -f -k {ksize} -x {table_size} -N {n_tables} '\
          '-C {coverage} -R {report_fn} {ct_out_str} {inputs}'.format(**locals())

    targets = [fn + '.keep' for fn in input_files]
    targets.append(report_fn)
    if ct_out_str:
        targets.append(ct_outfn)

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'file_dep': input_files,
            'targets': targets,
            'clean': [clean_targets]}

@create_task_object
def download_and_gunzip_task(url, target_fn, label=''):
    cmd = 'curl {url} | gunzip -c > {target_fn}'.format(**locals())

    name = '_'.join(['download_gunzip', target_fn, label])

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'targets': [target_fn],
            'clean': [clean_targets],
            'uptodate': [run_once]}

@create_task_object
def download_and_untar_task(url, target_dir, label=''):

    cmd1 = 'mkdir -p {target_dir}; curl {url} | tar -xz -C {target_dir}'.format(**locals())
    name = '_'.join(['download_untar', target_dir.strip('/'), label])
    done = name + '.done'
    cmd2 = 'touch {name}'.format(name=name)

    return {'name': name,
            'title': title_with_actions,
            'actions': [cmd1, cmd2],
            'targets': [done],
            'clean': [(clean_folder, [target_dir])],
            'uptodate': [run_once]}

@create_task_object
def create_folder_task(folder, label=''):

    if not label:
        label = 'create_folder_{folder}'.format(**locals())

    return {'title': title_with_actions,
            'name': label,
            'actions': [(create_folder, [folder])],
            'targets': [folder],
            'uptodate': [run_once],
            'clean': [clean_targets] }

@create_task_object
def blast_format_task(db_fn, db_out_fn, db_type):
    assert db_type in ['nucl', 'prot']

    cmd = 'makeblastdb -in {db_fn} -dbtype {db_type} -out {db_out_fn}'.format(**locals())

    target_fn = ''
    if db_type == 'nucl':
        target_fn = db_out_fn + '.nhr'
    else:
        target_fn = db_out_fn + '.phr'

    name = 'makeblastdb_{db_out_fn}'.format(**locals())

    return {'name': name,
            'title': title_with_actions,
            'actions': [cmd, 'touch '+db_out_fn],
            'targets': [target_fn, db_out_fn],
            'file_dep': [db_fn],
            'clean': [clean_targets, 'rm -f {target_fn}.*'.format(**locals())] }

@create_task_object
def link_file_task(src):
    ''' Soft-link file to the current directory
    '''
    cmd = 'ln -fs {src}'.format(src=src)
    return {'title': title_with_actions,
            'name': 'ln_' + os.path.basename(src),
            'actions': [cmd],
            'targets': [os.path.basename(src)],
            'uptodate': [run_once],
            'clean': [clean_targets]}

@create_task_object
def bowtie2_build_task(input_fn, db_basename, bowtie2_cfg):

    extra_args = bowtie2_cfg['extra_args']
    cmd = 'bowtie2-build {extra_args} {input_fn} {db_basename}'.format(**locals())
    
    targets = [db_basename+ext for ext in \
                ['.1.bt2', '.2.bt2', '.3.bt2', '.4.bt2', '.rev.1.bt2', '.rev.2.bt2']]
    targets.append(db_basename)

    name = 'bowtie2_build_{db_basename}'.format(**locals())
    return {'title': title_with_actions,
            'name': db_basename,
            'actions': [cmd, 'touch {db_basename}'.format(**locals())],
            'targets': targets,
            'file_dep': [input_fn],
            'clean': [clean_targets] }

@create_task_object
def bowtie2_align_task(db_basename, target_fn, bowtie2_cfg, left_fn='', right_fn='', singleton_fn='',
                        read_fmt='-q', samtools_convert=True,
                        encoding='phred33'):

    assert read_fmt in ['-q', '-f']
    assert encoding in ['phred33', 'phred64']
    encoding = '--' + encoding
    if (left_fn or right_fn):
        assert (left_fn and right_fn)
    n_threads = bowtie2_cfg['n_threads']
    extra_args = bowtie2_cfg['extra_args']
    cmd = 'bowtie2 -p {n_threads} {extra_args} {encoding} {read_fmt} -x {db_basename} '.format(**locals())
    
    file_dep = [db_basename]
    targets = []

    name = 'bowtie2_align' + ''.join('+' + fn if fn else fn for fn in [left_fn, right_fn, singleton_fn, db_basename])

    if left_fn:
        file_dep.extend([left_fn, right_fn])
        left_fn = '-1 ' + left_fn
        right_fn = '-2 ' + right_fn
    if singleton_fn:
        file_dep.append(singleton_fn)
        singleton_fn = '-U ' + singleton_fn
    if samtools_convert:
        targets.append(target_fn + '.bam')
        target_fn = ' | samtools view -Sb - > {target_fn}.bam'.format(**locals())
    else:
        targets.append(target_fn)
        target_fn = '-S ' + target_fn

    cmd = cmd + '{left_fn} {right_fn} {singleton_fn} {target_fn}'.format(**locals())

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'targets': targets,
            'file_dep': file_dep,
            'clean': [clean_targets] }
@create_task_object
def trimmomatic_pe_task(left_in, right_in, left_paired_out, left_unpaired_out, 
                     right_paired_out, right_unpaired_out, encoding, trim_cfg):

    assert encoding in ['phred33', 'phred64']
    name = 'TrimmomaticPE_' + left_in + '_' + right_in

    params = trim_cfg['params']
    n_threads = trim_cfg['n_threads']
    cmd = 'TrimmomaticPE -{encoding} -threads {n_threads} {left_in} {right_in} {left_paired_out} {left_unpaired_out} '\
          '{right_paired_out} {right_unpaired_out} {params}'.format(**locals())

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'file_dep': [left_in, right_in],
            'targets': [left_paired_out, left_unpaired_out, right_paired_out, right_unpaired_out],
            'clean': [clean_targets]}

@create_task_object
def trimmomatic_se_task(sample_fn, output_fn, encoding, trim_cfg):
    assert encoding in ['phred33', 'phred64']
    name = 'TrimmomaticSE_' + sample_fn

    params = trim_cfg['params']
    n_threads = trim_cfg['n_threads']
    cmd = 'TrimmomaticSE -{encoding} -threads {n_threads} {sample_fn} '\
          '{output_fn} {params}'.format(**locals())

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'file_dep': [sample_fn],
            'targets': [output_fn],
            'clean': [clean_targets]}

@create_task_object
def interleave_task(left_in, right_in, out_fn, label=''):

    if not label:
        label = 'interleave_' + out_fn

    cmd = 'interleave-reads.py {left_in} {right_in} -o {out_fn}'.format(**locals())

    return {'title': title_with_actions,
            'name': label,
            'actions': [cmd],
            'file_dep': [left_in, right_in],
            'targets': [out_fn],
            'clean': [clean_targets]}

@create_task_object
def cat_task(file_list, target_fn):

    cmd = 'cat {files} > {t}'.format(files=' '.join(file_list), t=target_fn)

    return {'title': title_with_actions,
            'name': 'cat_' + target_fn,
            'actions': [cmd],
            'file_dep': file_list,
            'targets': [target_fn],
            'clean': [clean_targets]}

@create_task_object
def group_task(group_name, task_names):
    return {'name': group_name,
            'actions': None,
            'task_dep': task_names}

# python3 BUSCO_v1.1b1/BUSCO_v1.1b1.py -in petMar2.cdna.fa -o petMar2.cdna.busco.test -l vertebrata/ -m trans -c 4
@create_task_object
def busco_task(input_filename, output_dir, busco_db_dir, input_type, busco_cfg, label=''):
    
    name = '_'.join(['busco', input_filename, os.path.basename(busco_db_dir), label])

    assert input_type in ['genome', 'OGS', 'trans']
    n_threads = busco_cfg['n_threads']
    busco_path = busco_cfg['path']

    cmd = 'python3 {busco_path} -in {in_fn} -o {out_dir} -l {db_dir} -m {in_type} -c {n_threads}'.format(
            busco_path=busco_path, in_fn=input_filename, out_dir=output_dir, db_dir=busco_db_dir, 
            in_type=input_type, n_threads=n_threads)

    return {'name': name,
            'title': title_with_actions,
            'actions': [cmd],
            'targets': [output_dir],
            'file_dep': [input_filename],
            'uptodate': [run_once],
            'clean': [(clean_folder, [output_dir])]}

