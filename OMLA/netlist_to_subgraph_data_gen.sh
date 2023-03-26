#!/bin/bash
DES=c1355
nohup perl netlist_to_subgraphs_cluster_version.pl -f ${DES}_resyn -i ../circuit_datasets/${DES}_resynRelockedResyn > log_graphDataGen_${DES}_resyn.txt 2>&1 &
nohup perl netlist_to_subgraphs_cluster_version.pl -f ${DES}_random -i ../circuit_datasets/${DES}_resynRelockedRandomSyn > log_graphDataGen_${DES}_randomSyn.txt 2>&1 &
