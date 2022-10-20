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
from models.graphcnn import GraphCNN
criterion = nn.CrossEntropyLoss()

def train(args, model, device, train_graphs, optimizer, epoch):
    model.train()
    total_iters = args.iters_per_epoch
    pbar = tqdm(range(total_iters), unit='batch')
    loss_accum = 0
    for pos in pbar:
        selected_idx = np.random.permutation(len(train_graphs))[:args.batch_size]
        batch_graph = [train_graphs[idx] for idx in selected_idx]
        output = model(batch_graph)
        labels = torch.LongTensor([graph.label for graph in batch_graph]).to(device)
        loss = criterion(output, labels)
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        loss = loss.detach().cpu().numpy()
        loss_accum += loss
        pbar.set_description('epoch: %d' % (epoch))
    average_loss = loss_accum/total_iters
    print("loss training: %f" % (average_loss))
    return average_loss

def pass_data_iteratively(model, graphs, minibatch_size = 64):
    model.eval()
    output = []
    idx = np.arange(len(graphs))
    for i in range(0, len(graphs), minibatch_size):
        sampled_idx = idx[i:i+minibatch_size]
        if len(sampled_idx) == 0:
            continue
        output.append(model([graphs[j] for j in sampled_idx]).detach())
    return torch.cat(output, 0)

def test(args, model, device, train_graphs, test_graphs, epoch,val):
    model.eval()
    output = pass_data_iteratively(model, train_graphs)
    pred = output.max(1, keepdim=True)[1]
    labels = torch.LongTensor([graph.label for graph in train_graphs]).to(device)
    correct = pred.eq(labels.view_as(pred)).sum().cpu().item()
    acc_train = correct / float(len(train_graphs))
    loss_train = criterion(output, labels)
    loss_train = loss_train.detach().cpu().numpy()
    output = pass_data_iteratively(model, test_graphs)
    pred = output.max(1, keepdim=True)[1]
    labels = torch.LongTensor([graph.label for graph in test_graphs]).to(device)
    correct = pred.eq(labels.view_as(pred)).sum().cpu().item()
    acc_test = correct / float(len(test_graphs))
    TP=0
    FP=0
    TN=0
    FN=0
    i=0
    for l in labels.view_as(pred):
        if not val:#new
            print("keygate index is:")
            print(str(test_graphs[i].keygate))#new
        print("True is "+str(l)+" predicted is "+str(pred[i]))
        if pred[i]==1:
            if l==1:
                TP=TP+1
            else:
                FP=FP+1
        else:
            if l==0:
                TN=TN+1
            else:
                FN=FN+1
        i=i+1
    if TP+FP != 0:
        prec_test=(TP/(TP+FP))*100
    else:
        prec_test=100

    loss_test = criterion(output, labels)
    loss_test = loss_test.detach().cpu().numpy()
    if val:
        print("accuracy train: %f val: %f" % (acc_train, acc_test))
        print("loss train: %f val: %f" % (loss_train, loss_test))
        print("Precision Val is: "+str(prec_test))
    else:
        print("accuracy train: %f test: %f" % (acc_train, acc_test))
        print("Precision Test is: "+str(prec_test))
    return acc_train, acc_test, loss_train, loss_test, prec_test, TP, FP, TN, FN

class OMLATrainer:
    def __init__(self,parentFolder,links_name,device):
        self.parentFolder = parentFolder
        self.links_name = links_name
        self.device = device
        self.links_dir = os.path.join(self.parentFolder,'{}'.format(self.links_name))
        self.train_pos_dir = os.path.join(self.parentFolder,'{}'.format('node_tr_pos.txt'))
        self.train_neg_dir = os.path.join(self.parentFolder,'{}'.format('node_tr_neg.txt'))
        self.valid_pos_dir = os.path.join(self.parentFolder,'{}'.format('node_va_pos.txt'))
        self.valid_neg_dir = os.path.join(self.parentFolder,'{}'.format('node_va_neg.txt'))
        self.test_pos_dir = os.path.join(self.parentFolder,'{}'.format('node_te_pos.txt'))
        self.test_neg_dir = os.path.join(self.parentFolder,'{}'.format('node_te_neg.txt'))
        
    def balanceSamples(self,posList,negList):
        lenPos = len(posList)
        lenNeg = len(negList)
        if(lenPos>lenNeg):
            print("We have imbalance. Pos > Neg")
            np.random.shuffle(posList)
            tempList=posList[:lenNeg]
            posList=tempList
        elif(lenNeg>lenPos):
            print("We have imbalance. Neg > Pos")
            np.random.shuffle(negList)
            tempList=posList[:lenPos]
            negList=tempList
        return postList,negList
            
    def prepareData(self,args):
        links_idx = np.loadtxt(self.links_dir, dtype=int)
        links_pos = (links_idx[:, 0], links_idx[:, 1])
        
        # Train dataset
        self.train_pos = np.loadtxt(self.train_pos_dir, dtype=int)
        self.train_neg = np.loadtxt(self.train_neg_dir, dtype=int)
        self.train_pos,self.train_neg = self.balanceSamples(self.train_pos,self.train_neg)
        print("Length of train neg is "+str(len(self.train_neg))+" and length of train positive is "+str(len(self.train_pos)))
        
        # Validation dataset
        self.valid_pos = np.loadtxt(self.valid_pos_dir, dtype=int)
        self.valid_neg = np.loadtxt(self.valid_neg_dir, dtype=int)
        self.valid_pos,self.valid_neg = self.balanceSamples(self.valid_pos,self.valid_neg)
        print("Length of valid neg is "+str(len(self.valid_neg))+" and length of valid positive is "+str(len(self.valid_pos)))
        
        # Test dataset
        self.test_pos = np.loadtxt(self.test_pos_dir, dtype=int)
        self.test_neg = np.loadtxt(self.test_neg_dir, dtype=int)
        
        #test_idx=np.concatenate([self.test_pos.copy(),self.test_neg.copy()])
        feats_test = np.loadtxt(os.path.join(self.parentFolder,'feat.txt'), dtype='float32')
        count = np.loadtxt(os.path.join(self.parentFolder,'count.txt'))
        cell = np.genfromtxt(os.path.join(self.parentFolder,'cell.txt'), dtype=str)
        
        arr1inds = count.argsort()
        sorted_count = count[arr1inds[0::]]
        self.attributes = feats_test[arr1inds[0::]]
        sorted_cell = cell[arr1inds[0::]]
        
        max_idx = np.max(links_idx)
        self.net = ssp.csc_matrix((np.ones(len(links_idx)), (links_idx[:, 0], links_idx[:, 1])), shape=(max_idx+1, max_idx+1) )

        self.net[np.arange(max_idx+1), np.arange(max_idx+1)] = 0  # remove self-loops
        self.B=self.net.copy() # a matrix without semmetric edges
        self.B.eliminate_zeros()
        self.net[links_idx[:, 1], links_idx[:, 0]] = 1  # add symmetric edges
        self.net[np.arange(max_idx+1), np.arange(max_idx+1)] = 0  # remove self-loops
        
        self.A = self.net.copy()  # the observed network
        self.A.eliminate_zeros()  # make sure the links are masked when using the sparse matrix in scipy-1.3.x
        node_information = self.attributes
        self.train_graphs, self.test_graphs,self.val_graphs = keygates2subgraphs(
            self.A,
            self.B,
            self.train_pos,
            self.train_neg,
            self.test_pos,
            self.test_neg,
            self.val_pos,
            self.val_neg,
            args.hop,
            node_information,
            args.no_parallel,
            args.use_dis
        )
        
        random.shuffle(self.train_graphs)
        if args.split_val: #In case you want to shuffle and get 10% for validation
            self.train_graphs.extend(self.val_graphs)
            val_num = int(0.1 * len(self.train_graphs))
            self.val_graphs = self.train_graphs[:val_num]
            self.train_graphs = self.train_graphs[val_num:]
        print('# train: %d, # test: %d' % (len(self.train_graphs), len(self.test_graphs)))
        
    def createModel(self,args,device):
        self.model = GraphCNN(args.num_layers, args.num_mlp_layers, self.train_graphs[0].node_features.shape[1], \
            args.hidden_dim, num_classes=2, args.final_dropout, args.learn_eps, args.graph_pooling_type, \
                args.neighbor_pooling_type, device).to(device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=args.lr)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=50, gamma=0.5)
        
    def trainAndTestOMLA(self,args,epoch):
        loss = train(args,self.model,self.device,self.train_graphs,self.optimizer,epoch)
        acc_train, acc_val, loss_train,val_loss,prec_val, TP,FP,TN,FN = test(args,self.model,self.device,self.train_graphs,\
            self.val_graphs, epoch,True)
        self.scheduler.step()
        return acc_train, acc_val, loss_train,val_loss,prec_val, TP,FP,TN,FN
    
    def testOMLA(self,args,epoch):
        acc_train, acc_test, loss_train,loss_test,prec_test,TP,FP,TN,FN = test(args, self.model,self.device,self.train_graphs,\
            self.test_graphs, epoch,False)
        return acc_train,acc_test, loss_train,loss_test,prec_test,TP,FP,TN,FN
    
    def getOMLAModel(self):
        return self.model