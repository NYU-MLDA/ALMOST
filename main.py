import torch
import numpy as np
import sys, copy, math, time, pdb
import pickle
import scipy.io as sio
import scipy.sparse as ssp
import os.path
import random
import argparse
from util_functions import *
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from tqdm import tqdm
from trainer import OMLATrainer

def main():
    parser = argparse.ArgumentParser(description='OMLA Attack')
    # general settings
    parser.add_argument('--data-name', default=None, help='network name')
    parser.add_argument('--file-name', default=None, help='dataset file name')
    parser.add_argument('--links-name', default=None, help='links name')
    parser.add_argument('--only-predict', action='store_true', default=False,
                        help='if True, will load the saved model and output predictions\
                        for the testing nodes; you still need to specify links-name\
                        in order to build the observed network and extract subgraphs')
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--no-parallel', action='store_true', default=False,
                        help='if True, use single thread for subgraph extraction; \
                        by default use all cpu cores to extract subgraphs in parallel')
    # model settings
    parser.add_argument('--hop', default=1, metavar='S',
                        help='enclosing subgraph hop number, \
                        options: 1, 2,..., "auto"')
    parser.add_argument('--split-val', action='store_true', default=False,
                        help='whether to split validation')
    parser.add_argument('--use-dis', action='store_true', default=False,
                        help='whether to use distance encoding')
    parser.add_argument('--use-attribute', action='store_true', default=False,
                        help='whether to use node attributes')
    parser.add_argument('--save-model', action='store_true', default=False,
                        help='save the final model')

    parser.add_argument('--device', type=int, default=0,
                            help='which gpu to use if any (default: 0)')
    parser.add_argument('--batch_size', type=int, default=32,
                            help='input batch size for training (default: 32)')
    parser.add_argument('--iters_per_epoch', type=int, default=50,
                            help='number of iterations per each epoch (default: 50)')
    parser.add_argument('--epochs', type=int, default=350,
                            help='number of epochs to train (default: 350)')
    parser.add_argument('--lr', type=float, default=0.01,
                            help='learning rate (default: 0.01)')
    parser.add_argument('--num_layers', type=int, default=5,
                            help='number of layers INCLUDING the input one (default: 5)')
    parser.add_argument('--num_mlp_layers', type=int, default=2,
                            help='number of layers for MLP EXCLUDING the input one (default: 2). 1 means linear model.')
    parser.add_argument('--hidden_dim', type=int, default=64,
                            help='number of hidden units (default: 64)')
    parser.add_argument('--final_dropout', type=float, default=0.5,
                            help='final layer dropout (default: 0.5)')
    parser.add_argument('--graph_pooling_type', type=str, default="sum", choices=["sum", "average"],
                            help='Pooling for over nodes in a graph: sum or average')
    parser.add_argument('--neighbor_pooling_type', type=str, default="sum", choices=["sum", "average", "max"],
                            help='Pooling for over neighboring nodes: sum, average or max')
    parser.add_argument('--learn_eps', action="store_true",
                                            help='Whether to learn the epsilon weighting for the center nodes. Does not affect training accuracy though.')
    parser.add_argument('--degree_as_tag', action="store_true",
                            help='let the input node features be the degree of nodes (heuristics for unlabeled graph)')
    parser.add_argument('--filename', type = str, default = "",
                                            help='output file')

    args = parser.parse_args()
    seed_everything()
    device = torch.device("cuda:" + str(args.device)) if torch.cuda.is_available() else torch.device("cpu")
    dataFolder
    dumpFolder
    args.hop = int(args.hop)
    omlaTrainObj = OMLATrainer(dataFolder,"link.txt",device)
    omlaTrainObj.prepareData(args)
    omlaTrainObj.createModel()
    
    best_loss = None
    best_epoch = None
    best_test=None
    

    for epoch in range(1, args.epochs + 1):
        acc_train, acc_val, loss_train,val_loss,prec_val, TP,FP,TN,FN = omlaTrainObj.trainAndTestOMLA(args,epoch)
        if not args.filename == "":
            with open(args.filename, 'a') as f:
                f.write("Epoch: %d Training loss: %f Train_Accuracy: %f Validation accuracy: %f" % (epoch, avg_loss, acc_train, acc_val))
                f.write("\n")
        print("")
        if best_loss is None:
            best_loss = val_loss
        if val_loss <= best_loss:
            print("Epoch "+str(epoch)+"Is better, performing testing")
            best_loss = val_loss
            best_epoch = epoch
            _, acc_test, loss_train,loss_test,prec_test,TP,FP,TN,FN = omlaTrainObj.testOMLA(args,epoch)
            model_name = osp.join(dataFolder,'model_model.pth')
            print('Saving final model states to {}...'.format(model_name))
            torch.save(model.state_dict(), model_name)
            hyper_name = osp.join(dataFolder,'model_hyper.pkl')
            with open(hyper_name, 'wb') as hyperparameters_file:
                pickle.dump(args, hyperparameters_file)
                print('Saving hyperparameters to {}...'.format(hyper_name))
            if not args.filename == "":
                with open(args.filename, 'a') as f:
                    f.write("Epoch is best: %d Training loss: %f Train_Accuracy: %f Test accuracy: %f" % (epoch, avg_loss, acc_train, acc_test))
                    f.write("\n")
                    f.write("TP: %d FP: %d TN: %d FN: %d" % (TP,FP,TN,FN))
                    f.write("\n")
        print(model.eps)
    if not args.filename == "":
        with open(args.filename, 'a') as f:
            f.write("Best test for epoch %d Accuracy: %f Precision: %f" % (best_epoch, acc_test,prec_test))
            f.write("\n")
            
if __name__ == "__main__":
    main()