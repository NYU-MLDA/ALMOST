#!/bin/bash

KEYSIZE=64 #128 for relocking
DES=c1355
perl RLL_netlist.pl -a 4 -lib 45 -k ${KEYSIZE} -i ../bench/synthesized/${DES}_syn.v -o ../locked_netlists/${DES}/ -f locked_${DES}_k${KEYSIZE}_orig.v
