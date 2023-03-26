import torch
import numpy as np
import sys, copy, math, time, pdb
import pickle
import scipy.io as sio
import scipy.sparse as ssp
import os.path as osp
import os
import random
import argparse
from util_functions import seed_everything
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from tqdm import tqdm
from trainer import OMLATrainer
from resynthesis import Resynthesizer
from SAhandler import SAHandler
from models.graphcnn import GraphCNN
from evaluator import OMLAEvaluator
#from util_functions_orig import *
from util_functions import *

#criterion = nn.CrossEntropyLoss()


def prepareData(args,parentFolder,links_name):
    a_list=[]
    val_pos, val_neg, train_pos, test_pos,train_neg,test_neg,link_pos = None,None, None, None,None,None,None
    print("The link file was provided")
    args.links_dir = os.path.join(parentFolder,'{}'.format(links_name))
    links_idx = np.loadtxt(args.links_dir, dtype=int)
    links_pos = (links_idx[:, 0], links_idx[:, 1])
    args.train_dir = os.path.join(parentFolder,'{}'.format('node_tr_pos.txt'))
    train_pos = np.loadtxt(args.train_dir, dtype=int)
    args.train_dir = os.path.join(parentFolder,'{}'.format('node_tr_neg.txt'))
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

    args.train_dir = os.path.join(parentFolder,'{}'.format('node_va_pos.txt'))
    val_pos = np.loadtxt(args.train_dir, dtype=int)


    args.train_dir = os.path.join(parentFolder,'{}'.format('node_va_neg.txt'))
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
    args.train_dir =os.path.join(parentFolder,'{}'.format('node_te_pos.txt'))
    test_pos = np.loadtxt(args.train_dir, dtype=int)

    test_idxx = np.loadtxt(args.train_dir, dtype=int)
    a_list.append(test_idxx)


    args.train_dir = os.path.join(parentFolder,'{}'.format('node_te_neg.txt'))
    test_neg = np.loadtxt(args.train_dir, dtype=int)



    test_idx2 = np.loadtxt(args.train_dir, dtype=int)
    a_list.append(test_idx2)
    test_idx=np.concatenate(a_list)

    print("All done!")

    cell=[]
    feat=[]
    count=[]
    feats_test = np.loadtxt(os.path.join(parentFolder,'feat.txt'), dtype='float32')
    count = np.loadtxt(os.path.join(parentFolder,'count.txt'))
    cell = np.genfromtxt(os.path.join(parentFolder,'cell.txt'), dtype=str)
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
    # New data saving
    print('Before # train: %d, # test: %d' % (len(train_graphs), len(test_graphs)))
    random.shuffle(train_graphs)
    if args.split_val: #In case you want to shuffle and get 10% for validation
        train_graphs.extend(val_graphs)
        val_num = int(0.1 * len(train_graphs))
        val_graphs = train_graphs[:val_num]
        train_graphs = train_graphs[val_num:]
    print('After # train: %d, # test: %d' % (len(train_graphs), len(test_graphs)))
    return train_graphs, test_graphs,val_graphs

def main():
    parser = argparse.ArgumentParser(description='OMLA Attack')
    # general settings
    parser.add_argument('--design', default=None, help='network name')
    parser.add_argument('--orig_lock', default=None, help='Original folder of relocked circuits')
    parser.add_argument('--train_test', default=None, help='Train test circuits data folder')
    parser.add_argument('--feature_dir', default=None, help='Folder having feature information')
    parser.add_argument('--dump_dir', default=None, help='Dump directory')
    parser.add_argument('--lib', default=None, help='Dump directory')
    parser.add_argument('--only-predict', action='store_true', default=False,
                        help='if True, will load the saved model and output predictions\
                        for the testing nodes; you still need to specify links-name\
                        in order to build the observed network and extract subgraphs')
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--no-parallel', action='store_true', default=False,
                        help='if True, use single thread for subgraph extraction; \
                        by default use all cpu cores to extract subgraphs in parallel')
    parser.add_argument('--enable_sa', action='store_true', default=False,
                        help='If true, performs data augmentation with simulated annealing attack')
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
    parser.add_argument('--epochs', type=int, default=351,
                            help='number of epochs to train (default: 351)')
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
    num_classes=2
    #torch.manual_seed(0)
    #np.random.seed(0)
    #if torch.cuda.is_available():
    #    torch.cuda.manual_seed_all(0)
    device = torch.device("cuda:" + str(args.device)) if torch.cuda.is_available() else torch.device("cpu")
    origRelockedCktFolder = args.orig_lock
    trainTestFolder = args.train_test
    dataFolder=args.feature_dir
    dumpFolder=args.dump_dir
    validFileForSA = osp.join(trainTestFolder,"Test_"+args.design+"_k64_resyn.v")
    args.hop = int(args.hop)
    if not osp.exists(dumpFolder):
        os.mkdir(dumpFolder)
    if args.only_predict:
        omlaEvalObj = OMLAEvaluator(dataFolder,"link.txt",device='cuda')
        omlaEvalObj.prepareData()
        omlaEvalObj.loadPreTrainedModel()
        acc,x,y = omlaEvalObj.getOmlaAttackAccuracy()
        print("Test acc. {}".format(acc))
        print("x here")
        print(x)
        tsne = TSNE(n_components=2, verbose=1, random_state=123)
        z = tsne.fit_transform(x)
        df = pd.DataFrame()
        df["y"] = y
        df["comp-1"] = z[:,0]
        df["comp-2"] = z[:,1]
        X=z
        kmeans = KMeans(n_clusters=2)#, init='k-means++', max_iter=300, n_init=10, random_state=0)
        pred_y = kmeans.fit_predict(X)
        #clt_sim_matrix.fit(pred_y)
        plt.scatter(X[:,0],X[:,1],c=df.y.tolist() )
        plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1], s=300, c='red')
        plt.savefig(osp.join(dataFolder,'cluster'+args.design+'_v'+'_TSNE.png'))
        exit(0)
    omlaTrainObj = OMLATrainer(dataFolder,"link.txt",device)
    #omlaTrainObj.prepareData(args)
    #train_graphs,val_graphs,test_graphs = omlaTrainObj.getData()
    train_graphs, test_graphs,val_graphs = prepareData(args,dataFolder,"link.txt")
    omlaTrainObj.assignData(train_graphs, test_graphs,val_graphs)
    omlaTrainObj.createModel(args,device)
    
    #model = GraphCNN(args.num_layers, args.num_mlp_layers, train_graphs[0].node_features.shape[1], args.hidden_dim, num_classes, args.final_dropout, args.learn_eps, args.graph_pooling_type, args.neighbor_pooling_type, device).to(device)
    #optimizer = optim.Adam(model.parameters(), lr=args.lr)
    #scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=50, gamma=0.5)
    best_loss = None
    best_epoch = None
    best_test=None
    synID=0

    for epoch in range(1, args.epochs + 1):
        avg_loss,acc_train, acc_val, loss_train,val_loss,prec_val, TP,FP,TN,FN = omlaTrainObj.trainAndTestOMLA(args,epoch)
        #scheduler.step()
        #avg_loss = train(args, model, device, train_graphs, optimizer, epoch)
        #acc_train, acc_val, loss_train,val_loss,prec_val, TP,FP,TN,FN = test(args,model,device,train_graphs,val_graphs, epoch,True)
        if not args.filename == "":
            with open(args.filename, 'a') as f:
                f.write("Epoch: %d, trn_loss: %f, trn_acc: %f, val_loss: %f, val_acc: %f" % (epoch, avg_loss, acc_train,val_loss,acc_val))
                f.write("\n")
        if args.enable_sa and epoch % 50 == 0:
            print("\nRunning simulated annealing attack...")
            synID+=1
            saHandlerObj = SAHandler(validFileForSA,args.lib,dumpFolder,classifier=omlaTrainObj.getOMLAModel(),max_iterations=120)
            synthesisRecipe = saHandlerObj.runSimulatedAnnealingAttack()
            resynthesisObj = Resynthesizer(args.design,args.lib,synthesisRecipe,synID,origRelockedCktFolder,trainTestFolder,dataFolder)
            resynthesisObj.augmentNewData()
            print("\nAugmented new training and validation data..")
            train_graphs, test_graphs,val_graphs = prepareData(args,dataFolder,"link.txt")
            omlaTrainObj.assignData(train_graphs, test_graphs,val_graphs)
        if best_loss is None:
            #best_loss = val_loss
            best_loss = acc_val
        #if val_loss <= best_loss:
        if acc_val >= best_loss:
            print("Epoch "+str(epoch)+"Is better, performing testing")
            best_loss = val_loss
            best_loss=acc_val
            best_epoch = epoch
            _, acc_test, loss_train,loss_test,prec_test,TP,FP,TN,FN = omlaTrainObj.testOMLA(args,epoch)
            #_, acc_test, loss_train,loss_test,prec_test,TP,FP,TN,FN = test(args, model, device, train_graphs, test_graphs, epoch,False)
            model_name = osp.join(dataFolder,'model_model.pth')
            model_name_backup = osp.join(dumpFolder,'model_model.pth')
            print('Saving final model states to {}...'.format(model_name))
            print('Saving backup final model states to {}...'.format(model_name_backup))
            torch.save(omlaTrainObj.getOMLAModel().state_dict(), model_name)
            torch.save(omlaTrainObj.getOMLAModel().state_dict(), model_name_backup)
            #torch.save(model.state_dict(), model_name)
            hyper_name = osp.join(dataFolder,'model_hyper.pkl')
            hyper_name_backup = osp.join(dumpFolder,'model_hyper.pkl')
            with open(hyper_name_backup, 'wb') as hyperparameters_file:
                pickle.dump(args, hyperparameters_file)
                print('Saving hyperparameters to {}...'.format(hyper_name))
                print('Saving hyperparameters backup to {}...'.format(hyper_name_backup))
            if not args.filename == "":
                with open(args.filename, 'a') as f:
                    f.write("Best epoch: %d trn_loss: %f, trn_acc: %f, test_acc: %f" % (epoch, avg_loss, acc_train, acc_test))
                    f.write("\n")
                    f.write("TP: %d FP: %d TN: %d FN: %d" % (TP,FP,TN,FN))
                    f.write("\n")
        #print(omlaTrainObj.getOMLAModel().eps)
    if not args.filename == "":
        with open(args.filename, 'a') as f:
            f.write("Best test for epoch %d Accuracy: %f Precision: %f" % (best_epoch, acc_test,prec_test))
            f.write("\n")
            
if __name__ == "__main__":
    main()
