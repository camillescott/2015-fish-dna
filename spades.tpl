#!/bin/bash -login
#PBS -l walltime={{time}}
#PBS -l nodes=1:ppn={{n_threads}}
#PBS -l mem={{mem}}

#PBS -r n
#PBS -m abe
#PBS -W umask=027

{% if account is defined %}
#PBS -A {{account}}
{% endif %}
{% if email is defined %}
#PBS -M {{email}}
{% endif %}

cd $PBS_O_WORKDIR

export PATH={{bin}}:$PATH
{{bin}}/spades.py -o {{directory}} -k 21,27,33,39 --careful --cov-cutoff {{cov_cutoff}} -t {{n_threads}} {% for fn in file_list %} --pe{{loop.index}}-12 {{fn}} {% endfor %}

