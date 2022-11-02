#!/bin/bash
# Merge one day of TROPOMI l2 files to one l3 merged and re-gridded file
# Tuuli.Perttula@fmi.fi

# Create conda environment
#conda env create -f environment.yml -n tropomi


CURRENT_DATE=$(date '+%Y%m%d')
YESTERDAY=$(date --date="yesterday" +%Y%m%d)
echo "Yesterday: " $YESTERDAY

VARIABLE=${VARIABLE:-"no2-nrti"} #Options: no2-nrti, so2-nrti, co-nrti, o3-nrti'

RUNPATH="/kat/code/tropomi-l2-to-l3"

cmd="conda run -n tropomi python ${RUNPATH}/tropomi_l2_to_l3.py --var=${VARIABLE} --date=${YESTERDAY}"
echo $cmd
#eval $cmd
