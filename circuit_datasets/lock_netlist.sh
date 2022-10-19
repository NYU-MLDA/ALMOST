#!/bin/bash
DES_LIST=("c1355 c1908 c2670 c3540 c5315 c6288 c7552")
KEYSIZE=128 #128 for relocking
for DES in $DES_LIST
do
  for ((n=0; n<1000; n++))
  do
    perl RLL_self_referencing.pl -a 4 -lib 45 -k ${KEYSIZE} -i ${DES}/locked_${DES}_K64.v -o ${DES}/ -f Train_${DES}_syn_locked_rnd_64_relocked_K${KEYSIZE}_${n}.v
  done
done

for DES in $DES_LIST
do
  perl RLL_self_referencing.pl -a 4 -lib 45 -k ${KEYSIZE} -i ${DES}/locked_${DES}_K64.v -o ${DES}/ -f Validate_${DES}_syn_locked_rnd_64_relocked_K${KEYSIZE}_1.v
done
