#!/bin/bash

BATCH_SIZE=64
HIDDEN=128
LAYERS=8

export CUDA_VISIBLE_DEVICES=5
LIBRARY=/home/abc586/currentResearch/ALMOST_final/lib/nangate45.lib
DES=c1355
EPOCHS=2

WORK_DIR=/home/abc586/currentResearch/ALMOST_final/OMLA
MODE=resyn
nohup python main.py --use-dis --design ${DES} --epochs ${EPOCHS} --orig_lock ${WORK_DIR}/origRelockedCkt/${DES} --train_test ${WORK_DIR}/trainTestCkt/${DES} --dump_dir ${WORK_DIR}/dumpDataCkt/${DES}_${MODE} --feature_dir ${WORK_DIR}/graphDataCkt/${DES}_${MODE} --save-model --batch_size ${BATCH_SIZE} --filename ${MODE}_${DES}_result_b${BATCH_SIZE}_h2_fan_6layers_hd${HIDDEN}.txt  --hidden_dim ${HIDDEN} --lib ${LIBRARY} --num_layers ${LAYERS} > ${MODE}_log_${DES}_b${BATCH_SIZE}_h2_6layers_hd${HIDDEN}.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=6
MODE=random
nohup python main.py --use-dis --design ${DES} --epochs ${EPOCHS} --orig_lock ${WORK_DIR}/origRelockedCkt/${DES} --train_test ${WORK_DIR}/trainTestCkt/${DES} --dump_dir ${WORK_DIR}/dumpDataCkt/${DES}_${MODE} --feature_dir ${WORK_DIR}/graphDataCkt/${DES}_${MODE} --save-model --batch_size ${BATCH_SIZE} --filename ${MODE}_${DES}_result_b${BATCH_SIZE}_h2_fan_6layers_hd${HIDDEN}.txt  --hidden_dim ${HIDDEN} --lib ${LIBRARY} --num_layers ${LAYERS} > ${MODE}_log_${DES}_b${BATCH_SIZE}_h2_6layers_hd${HIDDEN}.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=7
MODE=sa
nohup python main.py --enable_sa --use-dis --design ${DES} --epochs ${EPOCHS} --orig_lock ${WORK_DIR}/origRelockedCkt/${DES} --train_test ${WORK_DIR}/trainTestCkt/${DES} --dump_dir ${WORK_DIR}/dumpDataCkt/${DES}_${MODE} --feature_dir ${WORK_DIR}/graphDataCkt/${DES}_${MODE} --save-model --batch_size ${BATCH_SIZE} --filename ${MODE}_${DES}_result_b${BATCH_SIZE}_h2_fan_6layers_hd${HIDDEN}.txt  --hidden_dim ${HIDDEN} --lib ${LIBRARY} --num_layers ${LAYERS} > ${MODE}_log_${DES}_b${BATCH_SIZE}_h2_6layers_hd${HIDDEN}.txt 2>&1 &
