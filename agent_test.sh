#!/usr/bin/env bash

# Set paths
scriptdir=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)
testdir=$scriptdir/test-data/
venv=$HOME/.isavenv/
mkdir tmp/
tmp=$scriptdir/tmp

# Set up venv and activate
virtualenv -q -p python3.5 $venv
source $venv/bin/activate
pip install isaagents==0.9.5 click==6.7

#planemo lint $scriptdir/agents/isa_create_metabo/isa_create_metabo.xml
#planemo test $scriptdir/agents/isa_create_metabo/isa_create_metabo.xml

$scriptdir/cli.py --galaxy_parameters_file=$scriptdir/agents/create_metabo/test-data/galaxy_inputs.json --target_dir=$tmp/


# Deactivate venv and cleanup
deactivate
rm -rf $venv