#!/bin/bash -login
#PBS -l walltime={{time}}
#PBS -l nodes=1:ppn={{n_threads}}
#PBS -l mem={{mem}}

#PBS -r n
#PBS -m abe
#PBS -W umask=027
{% if account is defined %}#PBS -A {{account}} {% endif %}
{% if email is defined %}#PBS -M {{email}} {% endif %}

cd $PBS_O_WORKDIR

abyss-pe name={{name}} k={{k}} in='{{files}}' np={{n_threads}}
