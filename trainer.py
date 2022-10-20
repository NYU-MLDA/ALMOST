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

def test_new(args, model, device, test_graphs):
    model.eval()
    output = pass_data_iteratively(model, test_graphs)
    pred = output.max(1, keepdim=True)[1]
    labels = torch.LongTensor([graph.label for graph in test_graphs]).to(device)
    correct = pred.eq(labels.view_as(pred)).sum().cpu().item()
    #correct = pred.eq(labels.view_as(pred)).sum().cpu().item()
    acc_test = correct / float(len(test_graphs))
    print("accuracy test: %f" % (acc_test))
    return acc_test, labels, pred

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