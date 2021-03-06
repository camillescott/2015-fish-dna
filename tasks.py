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

def create_folder_task(folder):

    return {'name': 'create_folder_' + folder,
            'title': title_with_actions,
            'actions': [(create_folder, [folder])]}

@create_task_object
def kmergenie_task(sample_list, kmergenie_cfg):
    
    prefix = kmergenie_cfg['prefix']
    params = kmergenie_cfg['params']
    n_threads = kmergenie_cfg['n_threads']
    sample_file = '.'.join([prefix, 'samples', 'txt'])

    def mksample_file():
        with open(sample_file, 'wb') as fp:
            for sample in sample_list:
                fp.write(sample + '\n')

    cmd = 'kmergenie {sample_file} {params} -o {prefix} -t {n_threads}'.format(**locals())

    return {'name': 'kmergenie_' + prefix,
            'title': title_with_actions,
            'actions': [(mksample_file, []), cmd],
            'file_dep': sample_list,
            'targets': [sample_file],
            'clean': [clean_targets]}

@create_task_object
def fastqc_task(sample_fn, fastqc_cfg):

    n_threads = fastqc_cfg['n_threads']

    cmd = 'fastqc -t {n_threads} {sample_fn}'.format(**locals())

    return {'name': 'fastqc_' + sample_fn,
            'title': title_with_actions,
            'actions': [cmd],
            'file_dep': [sample_fn],
            'uptodate': [run_once],
            'clean': [clean_targets]}

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
def build_spades_task(file_list, template_fn, cur_time, spades_cfg, pbs_cfg, label=''):

    if not label:
        label = 'spades_' + '_'.join(file_list)

    with open(template_fn) as fp:
        template = jinja2.Template(fp.read())

    script_fn = cur_time + '-' + spades_cfg['script_file']
    spades_cfg['directory'] = cur_time + '-' + spades_cfg['directory']

    spades_cfg.update(pbs_cfg)
    def create_script(file_list, spades_cfg, tpl):
        with open(script_fn, 'wb') as fp:
            pbs = tpl.render(file_list=file_list, **spades_cfg)
            fp.write(pbs)

    #cmd = 'qsub {fn}'.format(fn=script_fn)

    return {'title': title_with_actions,
            'name': label,
            'actions': [(create_script, [file_list, spades_cfg, template])],
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
def diginorm_task(input_fn, output_fn, dg_cfg, load_ct=None, save_ct=None):

    ksize = dg_cfg['ksize']
    table_size = dg_cfg['table_size']
    n_tables = dg_cfg['n_tables']
    coverage = dg_cfg['coverage']

    name = 'normalize_by_median:' + output_fn
    report_fn = output_fn + '.report.txt'

    file_dep = [input_fn]
    targets = [output_fn, report_fn]
    cmd = 'normalize-by-median.py -f -k {ksize} -x {table_size} -N {n_tables} '\
          '-C {coverage} -R {report_fn} -o {output_fn} '.format(**locals())
    
    if load_ct is not None:
        cmd += ' -l {} '.format(load_ct)
        file_dep.append(load_ct)

    if save_ct is not None:
        cmd += ' -s {} '.format(save_ct)
        targets.append(save_ct)

    cmd += input_fn

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'file_dep': file_dep,
            'targets': targets,
            'clean': [clean_targets]}

@create_task_object
def chained_twopass_diginorm_task(input_files, dg_cfg, label, ct_outfn):

    ksize = dg_cfg['ksize']
    table_size = dg_cfg['table_size']
    n_tables = dg_cfg['n_tables']
    coverage = dg_cfg['coverage']

    name = 'normalize_by_median_twopass_chained_' + label
    inputs = ' '.join(input_files)
    suffix = '.C{c}'.format(c=coverage)

    cmd_list = []
    targets = []
    for n, fn in enumerate(input_files + [fn + suffix for fn in input_files]):
        out_fn = fn + suffix
        report_fn = out_fn + '.report.txt'
        cmd = 'normalize-by-median.py -f -k {ksize} -x {table_size} -N {n_tables} '\
              '-C {coverage} -R {report_fn} -o {out_fn} -s {ct_outfn} '.format(**locals())
        if n > 0:
            cmd += '-l {ct_outfn} '.format(**locals())
        cmd += fn
        cmd_list.append(cmd)

        if n >= len(input_files):
            targets.append(out_fn)

    return {'title': title_with_actions,
            'name': name,
            'actions': cmd_list,
            'file_dep': input_files,
            'targets': targets,
            'clean': [clean_targets]}

@create_task_object
def load_counting_task(file_list, table_fn, counting_cfg, label):

    name = 'load_into_counting_' + table_fn + '_' + label

    table_size = counting_cfg['table_size']
    n_tables = counting_cfg['n_tables']
    ksize = counting_cfg['ksize']
    n_threads = counting_cfg['n_threads']

    cmd = 'load-into-counting.py -T {n_threads} -x {table_size} -N {n_tables} -k {ksize} '\
            '{table_fn} {inputs}'.format(inputs=' '.join(file_list), **locals())

    return {'name': name,
            'title': title_with_actions,
            'actions': [cmd],
            'file_dep': file_list,
            'targets': [table_fn],
            'clean': [clean_targets]}

@create_task_object
def abundance_dist_task(input_fn, table_fn, hist_fn):

    name = 'abundance_dist_' + hist_fn
    cmd = 'abundance-dist.py {table_fn} {input_fn} {hist_fn}'.format(**locals())

    return {'name': name,
            'title': title_with_actions,
            'actions': [cmd],
            'file_dep': [input_fn, table_fn],
            'targets': [hist_fn],
            'clean': [clean_targets]}

@create_task_object
def download_task(url, target_fn, label='default'):

    cmd = 'curl -o {target_fn} {url}'.format(**locals())
    name = '_'.join(['download_gunzip', target_fn, label])

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'targets': [target_fn],
            'clean': [clean_targets],
            'uptodate': [run_once]}

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
def link_file_task(src, dst=''):
    ''' Soft-link file to the current directory
    '''
    cmd = 'ln -fs {src} {dst}'.format(src=src, dst=dst)
    return {'title': title_with_actions,
            'name': 'ln_' + os.path.basename(src) + ('_' + dst if dst else ' '),
            'actions': [cmd],
            'file_dep': [src],
            'targets': [os.path.basename(src) if not dst else dst],
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
                     right_paired_out, right_unpaired_out, adapter_fn, encoding, trim_cfg):

    assert encoding in ['phred33', 'phred64']
    name = 'TrimmomaticPE_' + left_in + '_' + right_in

    params = trim_cfg['params']
    n_threads = trim_cfg['n_threads']
    cmd = 'java -jar $TRIM/trimmomatic-0.33.jar PE -{encoding} -threads {n_threads} {left_in} {right_in} {left_paired_out} {left_unpaired_out} '\
            '{right_paired_out} {right_unpaired_out} ILLUMINACLIP:{adapter_fn}:2:30:10 {params}'.format(**locals())

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'file_dep': [left_in, right_in, adapter_fn],
            'targets': [left_paired_out, left_unpaired_out, right_paired_out, right_unpaired_out],
            'clean': [clean_targets]}

@create_task_object
def trimmomatic_se_task(sample_fn, output_fn, adapter_fn, encoding, trim_cfg):
    assert encoding in ['phred33', 'phred64']
    name = 'TrimmomaticSE_' + sample_fn

    params = trim_cfg['params']
    n_threads = trim_cfg['n_threads']
    cmd = 'java -jar $TRIM/trimmomatic-0.33.jar SE -{encoding} -threads {n_threads} {sample_fn} '\
          '{output_fn} ILLUMINACLIP:{adapter_fn}:2:30:10 {params}'.format(**locals())

    return {'title': title_with_actions,
            'name': name,
            'actions': [cmd],
            'file_dep': [sample_fn, adapter_fn],
            'targets': [output_fn],
            'clean': [clean_targets]}

@create_task_object
def interleave_task(left_in, right_in, out_fn, label=''):

    if not label:
        label = 'interleave_' + out_fn

    cmd = 'interleave-reads.py --no-reformat {left_in} {right_in} -o {out_fn}'.format(**locals())

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
def busco_task(input_filename, output_dir, busco_db_dir, input_type, busco_cfg):
    
    name = '_'.join(['busco', input_filename, os.path.basename(busco_db_dir)])

    assert input_type in ['genome', 'OGS', 'trans']
    n_threads = busco_cfg['n_threads']
    busco_path = busco_cfg['path']

    cmd = 'python3 {busco_path} -in {in_fn} -o {out_dir} -l {db_dir} '\
            '-m {in_type} -c {n_threads}'.format(busco_path=busco_path, 
            in_fn=input_filename, out_dir=output_dir, db_dir=busco_db_dir, 
            in_type=input_type, n_threads=n_threads)

    return {'name': name,
            'title': title_with_actions,
            'actions': [cmd],
            'targets': ['run_' + output_dir, 
                        os.path.join('run_' + output_dir, 'short_summary_' + output_dir.rstrip('/'))],
            'file_dep': [input_filename],
            'uptodate': [run_once],
            'clean': [(clean_folder, ['run_' + output_dir])]}

@create_task_object
def quast_task(assemblies, quast_cfg, label):

    cmd = 'python {path}/quast.py {params} -L -m {min_length} -t {n_threads} -e --no-snps {files}'.format(
               files=' '.join(assemblies), **quast_cfg)

    return {'name': 'quast_' + label,
            'title': title_with_actions,
            'actions': [cmd],
            'targets': ['quast_results', 'quast_results/latest'],
            'file_dep': assemblies,
            'uptodate': [run_once],
            'clean': [(clean_folder, ['quast_results'])]}

