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


a_list=[]
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
torch.manual_seed(0)
np.random.seed(0)
device = torch.device("cuda:" + str(args.device)) if torch.cuda.is_available() else torch.device("cpu")
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(0)
print(args)
args.hop = int(args.hop)
'''Prepare data'''
args.file_dir = os.path.dirname(os.path.realpath('__file__'))
val_pos, val_neg, train_pos, test_pos,train_neg,test_neg,link_pos = None,None, None, None,None,None,None
if args.links_name is not None:
    print("The link file was provided")
    args.links_dir = os.path.join(args.file_dir, './data/{}/{}'.format(args.file_name,args.links_name))
    links_idx = np.loadtxt(args.links_dir, dtype=int)
    links_pos = (links_idx[:, 0], links_idx[:, 1])

if args.save_model: 
    print("Reading the nodes")
    args.train_dir = os.path.join(args.file_dir, './data/{}/{}'.format(args.file_name, 'node_tr_pos.txt'))
    train_pos = np.loadtxt(args.train_dir, dtype=int)
    args.train_dir = os.path.join(args.file_dir, './data/{}/{}'.format(args.file_name, 'node_tr_neg.txt'))
    train_neg = np.loadtxt(args.train_dir, dtype=int)
    if (len(train_neg)>len(train_pos)):
        print("We have imbalance. Neg > Pos")
        np.random.shuffle(train_neg)
        train_temp=train_neg[:len(train_pos)]
        train_neg=train_temp
    elif (len(train_pos)>len(train_neg)):
        print("We have imbalance. Pos > Neg")
        np.random.shuffle(train_pos)
        train_temp=train_pos[:len(train_neg)]
        train_pos=train_temp

    print("Length of train neg is "+str(len(train_neg))+" and length of train positive is "+str(len(train_pos)))

    args.train_dir = os.path.join(args.file_dir, './data/{}/{}'.format(args.file_name, 'node_va_pos.txt'))
    val_pos = np.loadtxt(args.train_dir, dtype=int)


    args.train_dir = os.path.join(args.file_dir, './data/{}/{}'.format(args.file_name, 'node_va_neg.txt'))
    val_neg = np.loadtxt(args.train_dir, dtype=int)


    if (len(val_neg)>len(val_pos)):
        print("We have imbalance. Neg > Pos")
        np.random.shuffle(val_neg)
        val_temp=val_neg[:len(val_pos)]
        val_neg=val_temp
    elif (len(val_pos)>len(val_neg)):
        print("We have imbalance. Pos > Neg")
        np.random.shuffle(val_pos)
        val_temp=val_pos[:len(val_neg)]
        val_pos=val_temp
args.train_dir = os.path.join(args.file_dir, './data/{}/{}'.format(args.file_name, 'node_te_pos.txt'))
test_pos = np.loadtxt(args.train_dir, dtype=int)

test_idxx = np.loadtxt(args.train_dir, dtype=int)
a_list.append(test_idxx)


args.train_dir = os.path.join(args.file_dir, './data/{}/{}'.format(args.file_name, 'node_te_neg.txt'))
test_neg = np.loadtxt(args.train_dir, dtype=int)



test_idx2 = np.loadtxt(args.train_dir, dtype=int)
a_list.append(test_idx2)
test_idx=np.concatenate(a_list)

print("All done!")

# build observed network
#if args.use_attribute: #
cell=[]
feat=[]
count=[]
feats_test = np.loadtxt('./data/{}/feat.txt'.format(args.file_name), dtype='float32')
count = np.loadtxt('./data/{}/count.txt'.format(args.file_name))
cell = np.genfromtxt('./data/{}/cell.txt'.format(args.file_name), dtype=str)
arr1inds = count.argsort()
sorted_count = count[arr1inds[0::]]
attributes = feats_test[arr1inds[0::]]
sorted_cell = cell[arr1inds[0::]]

max_idx = np.max(links_idx)
net = ssp.csc_matrix((np.ones(len(links_idx)), (links_idx[:, 0], links_idx[:, 1])), shape=(max_idx+1, max_idx+1) )

net[np.arange(max_idx+1), np.arange(max_idx+1)] = 0  # remove self-loops
B=net.copy() # a matrix without semmetric edges
B.eliminate_zeros()
net[links_idx[:, 1], links_idx[:, 0]] = 1  # add symmetric edges
net[np.arange(max_idx+1), np.arange(max_idx+1)] = 0  # remove self-loops

'''Train and apply classifier'''
A = net.copy()  # the observed network
A.eliminate_zeros()  # make sure the links are masked when using the sparse matrix in scipy-1.3.x

node_information = attributes

#if args.use_attribute and attributes is not None:
#    if node_information is not None:
#        node_information = np.concatenate([node_information, attributes], axis=1)
#    else:
#        node_information = attributes
#Newly added option
if args.only_predict:  
    print("Inside the only predict function")

    _, test_graphs,_ = keygates2subgraphs(
        A,
        B,
        None,
        None,
        test_pos,
        test_neg,
        None,
        None,
        args.hop,
        node_information,
        args.no_parallel,
        args.use_dis
    )
    print('# test: %d' % (len(test_graphs)))
else:
    train_graphs, test_graphs,val_graphs = keygates2subgraphs(
        A,
        B,
        train_pos,
        train_neg,
        test_pos,
        test_neg,
        val_pos,
        val_neg,
        args.hop,
        node_information,
        args.no_parallel,
        args.use_dis
    )

    

    print('# train: %d, # test: %d' % (len(train_graphs), len(test_graphs)))
   


num_classes=2

if args.only_predict:
    args.data_name='model'
    print("We are predicting")
    with open('./data/{}/{}_hyper.pkl'.format(args.file_name,args.data_name), 'rb') as hyperparameters_name:
        saved_args = pickle.load(hyperparameters_name)
    for key, value in vars(saved_args).items(): # replace with saved cmd_args
        vars(args)[key] = value
    classifier = GraphCNN(args.num_layers, args.num_mlp_layers, test_graphs[0].node_features.shape[1], args.hidden_dim, num_classes, args.final_dropout, args.learn_eps, args.graph_pooling_type, args.neighbor_pooling_type, device).to(device)
    if torch.cuda.is_available():
        classifier = classifier.cuda()
    model_name = './data/{}/{}_model.pth'.format(args.file_name,args.data_name)
    classifier.load_state_dict(torch.load(model_name))
    acc_test, labels, predictions = test_new(args, classifier, device,test_graphs)

    new_predictions=predictions.reshape(labels.shape[0],1)
    new_labels=labels.reshape(labels.shape[0],1)
    new_test_idx=test_idx.reshape(test_idx.shape[0],1)
    
    test_idx_and_pred = np.concatenate([new_test_idx, new_predictions, new_labels],1)
    pred_name = './data/{}/'.format(args.file_name) + 'h'+str(args.hop)+'_pred.txt'
    np.savetxt(pred_name, test_idx_and_pred, fmt=['%d', '%1.2f', '%d'])
    print('Predictions for {} are saved in {}'.format(args.test_name, pred_name))
    exit()
random.shuffle(train_graphs)
if args.split_val: #In case you want to shuffle and get 10% for validation
    train_graphs.extend(val_graphs)
    val_num = int(0.1 * len(train_graphs))
    val_graphs = train_graphs[:val_num]
    train_graphs = train_graphs[val_num:]
best_loss = None
best_epoch = None
best_test=None
model = GraphCNN(args.num_layers, args.num_mlp_layers, train_graphs[0].node_features.shape[1], args.hidden_dim, num_classes, args.final_dropout, args.learn_eps, args.graph_pooling_type, args.neighbor_pooling_type, device).to(device)

optimizer = optim.Adam(model.parameters(), lr=args.lr)
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=50, gamma=0.5)

for epoch in range(1, args.epochs + 1):
    scheduler.step()

    avg_loss = train(args, model, device, train_graphs, optimizer, epoch)
    acc_train, acc_val, loss_train,val_loss,prec_val, TP,FP,TN,FN = test(args,model,device,train_graphs,val_graphs, epoch,True)
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
        _, acc_test, loss_train,loss_test,prec_test,TP,FP,TN,FN = test(args, model, device, train_graphs, test_graphs, epoch,False)
        args.data_name='model'
        model_name = './data/{}/{}_model.pth'.format(args.file_name,args.data_name)
        print('Saving final model states to {}...'.format(model_name))
        torch.save(model.state_dict(), model_name)
        hyper_name = './data/{}/{}_hyper.pkl'.format(args.file_name,args.data_name)
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