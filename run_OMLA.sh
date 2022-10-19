#!/bin/bash

BATCH_SIZE=64
HIDDEN=64
LAYERS=6

#export CUDA_VISIBLE_DEVICES=0
#DES=c3540
#nohup python Main.py --split-val --use-dis --file-name ${DES} --save-model --links-name link.txt  --batch_size ${BATCH_SIZE} --filename Release_${DES}_result_b${BATCH_SIZE}_h2_fan_6layers_hd${HIDDEN}.txt  --hidden_dim ${HIDDEN} --num_layers ${LAYERS} > Release_log_${DES}_b${BATCH_SIZE}_h2_6layers_hd${HIDDEN}.txt 2>&1 &

#export CUDA_VISIBLE_DEVICES=2
#DES=c1908
#nohup python Main.py --split-val --use-dis --file-name ${DES} --save-model --links-name link.txt  --batch_size ${BATCH_SIZE} --filename Release_${DES}_result_b${BATCH_SIZE}_h2_fan_6layers_hd${HIDDEN}.txt  --hidden_dim ${HIDDEN} --num_layers ${LAYERS} > Release_log_${DES}_b${BATCH_SIZE}_h2_6layers_hd${HIDDEN}.txt 2>&1 &

export CUDA_VISIBLE_DEVICES=1
DES=c5315
nohup python Main.py --split-val --use-dis --file-name ${DES} --save-model --links-name link.txt  --batch_size ${BATCH_SIZE} --filename Release_${DES}_result_b${BATCH_SIZE}_h2_fan_6layers_hd${HIDDEN}.txt  --hidden_dim ${HIDDEN} --num_layers ${LAYERS} > Release_log_${DES}_b${BATCH_SIZE}_h2_6layers_hd${HIDDEN}.txt 2>&1 &

#export CUDA_VISIBLE_DEVICES=3
#DES=c2670
#nohup python Main.py --split-val --use-dis --file-name ${DES} --save-model --links-name link.txt  --batch_size ${BATCH_SIZE} --filename Release_${DES}_result_b${BATCH_SIZE}_h2_fan_6layers_hd${HIDDEN}.txt  --hidden_dim ${HIDDEN} --num_layers ${LAYERS} > Release_log_${DES}_b${BATCH_SIZE}_h2_6layers_hd${HIDDEN}.txt 2>&1 &

