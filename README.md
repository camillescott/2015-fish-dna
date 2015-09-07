# 2015-fish-dna Assembly Pipeline

## About 

A processing pipeline developed for an Illumina short-read de novo assembly project of an African cichlid.
It contains configuration and sample metadata, a pipeline implementation built with pydoit, and analyses
in IPython notebooks.

The data was generated by Russell Neches, and the pipeline in this repository was developed by Camille Scott.
Both are PhD students at UC Davis.

## Tutorial

### Dependencies

We recommend [anaconda](https://store.continuum.io/cshop/anaconda/) for managing python dependencies, or that
you use virtualenv to sandbox your environment. The instructions will be given for anaconda, but are applicable
to virtualenv installs as well. We will assume you are running on a debian system; dependencies
which are hosted in debian repositories may need to be installed manually on other platforms.

First, get our python dependencies: [pydoit](http://pydoit.org/), which is used to manage 
task dependencies; jinja2, a templating library; [khmer](https://github.com/dib-lab/khmer), 
a library for k-mer and short-read analysis; and [screed](https://github.com/dib-lab/screed), 
a FASTA/Q parsing library

    pip install pydoit jinja2 khmer screed


Install [fastqc](http://www.bioinformatics.babraham.ac.uk/projects/fastqc/), a program
for evaluating short-read sample quality:

	sudo apt-get install fastqc

Install [http://www.usadellab.org/cms/?page=trimmomatic](http://www.usadellab.org/cms/?page=trimmomatic). Trimmomatic is available in Ubuntu PPAs, but many HPC environments install it
in a non-standard way. So, we will install it manually. First, download the archive and unpack
it:

    mkdir -p $HOME/bin
    cd $HOME/bin
    curl -O http://www.usadellab.org/cms/uploads/supplementary/Trimmomatic/Trimmomatic-0.33.zip
	unzip Trimmomatic-0.33.zip

Now, export the Trimmomatic directory as an environment variable. On some HPC systems, 
the $TRIM variable may already be set, depending on local configuration.
For example, on the MSU HPCC, this is automatically set by loading the trimmomatic module,
and this step can be skipped:

	export TRIM=$HOME/bin/Trimmomatic-0.33

Install [kmergenie](http://kmergenie.bx.psu.edu/). First download and unpack it:

	cd $HOME/bin
	curl -O http://kmergenie.bx.psu.edu/kmergenie-1.6982.tar.gz
	tar -xvzf kmergenie-1.6982.tar.gz

kmergenie requires R; if you do not have it, it can be installed with:

    sudo apt-get install r-base-core

Otherwise, compile and install it:

    cd kmergenie-1.6982/
    sudo make install

Install [velvet](https://www.ebi.ac.uk/~zerbino/velvet/) assembler:

    sudo apt-get install velvet

### Running the Pipeline

There are two main scripts: `get_data`, which will download the FASTQ files, and `pipeline`,
which runs all the processing. The two are separate due to the sheer size of the files, which
may take a very long time to download, depending on your internet connection.