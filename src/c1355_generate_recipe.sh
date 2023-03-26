#!/bin/bash

RUNID=128
HOME_DIR=/home/abc586/currentResearch/ALMOST_final
NUM_RUNS=110
OPTIM_METRIC=6 # adversarial OMLA accuracy
DES=c1355

export CUDA_VISIBLE_DEVICES=5
MODEL_TYPE=random
nohup python runSA.py --benchmark ${HOME_DIR}/locked_netlists/${DES}/locked_${DES}_k64_orig.v --library ${HOME_DIR}/lib/nangate45.lib --dumpdir ${HOME_DIR}/dump/${DES}_${MODEL_TYPE} --runID ${RUNID} --runs ${NUM_RUNS} --metric ${OPTIM_METRIC} --modeldir ${HOME_DIR}/OMLA/dumpDataCkt/${DES}_${MODEL_TYPE}  > output_${DES}_${MODEL_TYPE}_runID${RUNID}.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=6
MODEL_TYPE=resyn
nohup python runSA.py --benchmark ${HOME_DIR}/locked_netlists/${DES}/locked_${DES}_k64_orig.v --library ${HOME_DIR}/lib/nangate45.lib --dumpdir ${HOME_DIR}/dump/${DES}_${MODEL_TYPE} --runID ${RUNID} --runs ${NUM_RUNS} --metric ${OPTIM_METRIC} --modeldir ${HOME_DIR}/OMLA/dumpDataCkt/${DES}_${MODEL_TYPE}  > output_${DES}_${MODEL_TYPE}_runID${RUNID}.txt 2>&1 &


export CUDA_VISIBLE_DEVICES=7
MODEL_TYPE=sa
nohup python runSA.py --benchmark ${HOME_DIR}/locked_netlists/${DES}/locked_${DES}_k64_orig.v --library ${HOME_DIR}/lib/nangate45.lib --dumpdir ${HOME_DIR}/dump/${DES}_${MODEL_TYPE} --runID ${RUNID} --runs ${NUM_RUNS} --metric ${OPTIM_METRIC} --modeldir ${HOME_DIR}/OMLA/dumpDataCkt/${DES}_${MODEL_TYPE}  > output_${DES}_${MODEL_TYPE}_runID${RUNID}.txt 2>&1 &
