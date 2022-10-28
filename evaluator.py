from dcm import dcm
from sklearn.cluster import KMeans
import pandas as pd
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
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
#from util import load_data, separate_data
from models.graphcnn import GraphCNN
import os.path as osp
num_classes = 2


class OMLAEvaluator:
    def __init__(self,parentFolder,links_name,preTrainedModel=None,device=None):
        self.parentFolder = parentFolder
        self.links_name = links_name
        self.preTrainedModel = preTrainedModel
        self.device = device
        self.links_dir = os.path.join(self.parentFolder,'{}'.format(self.links_name))
        self.pos_dir = os.path.join(self.parentFolder,'{}'.format('node_te_pos.txt'))
        self.neg_dir = os.path.join(self.parentFolder,'{}'.format('node_te_neg.txt'))
        
    def loadPreTrainedModel(self):
        if not self.preTrainedModel == None:
            print("Serious issue.. Recheck..")
            exit(0)
        num_classes=2
        sanityCheckPath(osp.join(self.parentFolder,'model_hyper.pkl'))
        sanityCheckPath(osp.join(self.parentFolder,'model_model.pth'))
        with open(osp.join(self.parentFolder,'model_hyper.pkl'),'rb') as hyperparameters_name:
            saved_args = pickle.load(hyperparameters_name)
        argsDict = {}
        for key, value in vars(saved_args).items(): # replace with saved cmd_args
            argsDict[key] = value
        classifier = GraphCNN(argsDict['num_layers'], argsDict['num_mlp_layers'],self.test_graphs[0].node_features.shape[1],argsDict['hidden_dim'], num_classes, argsDict['final_dropout'], \
            argsDict['learn_eps'], argsDict['graph_pooling_type'], argsDict['neighbor_pooling_type'], self.device).to(self.device)
        if torch.cuda.is_available():
            classifier = classifier.cuda()
        model_name = osp.join(self.parentFolder,'model_model.pth')
        classifier.load_state_dict(torch.load(model_name))
        self.preTrainedModel = classifier
        
    def pass_data_iteratively(self,graphs,minibatch_size = 64):
        self.preTrainedModel.eval()
        output = []
        idx = np.arange(len(graphs))
        for i in range(0, len(graphs), minibatch_size):
            sampled_idx = idx[i:i+minibatch_size]
            if len(sampled_idx) == 0:
                continue
            output.append(self.preTrainedModel([graphs[j] for j in sampled_idx]).detach())
        return torch.cat(output, 0)
    
    def test_new(self):
        self.preTrainedModel.eval()
        output = self.pass_data_iteratively(self.test_graphs)
        pred = output.max(1, keepdim=True)[1]
        labels = torch.LongTensor([graph.label for graph in self.test_graphs]).to(self.device)
        correct = pred.eq(labels.view_as(pred)).sum().cpu().item()
        correct = pred.eq(labels.view_as(pred)).sum().cpu().item()
        acc_test = correct / float(len(self.test_graphs))
        print("accuracy test: %f" % (acc_test))
        return acc_test, labels, pred
        
        
    def prepareData(self):
        links_idx = np.loadtxt(self.links_dir, dtype=int)
        links_pos = (links_idx[:, 0], links_idx[:, 1])
        self.test_pos = np.loadtxt(self.pos_dir, dtype=int)
        self.test_neg = np.loadtxt(self.neg_dir, dtype=int)
        
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
        
        node_information = None
        if self.attributes is not None:
            if node_information is not None:
                node_information = np.concatenate([node_information, self.attributes], axis=1)
            else:
                node_information = self.attributes

        _, test_graphs,_ = keygates2subgraphs(
                self.A,
                self.B,
                None,
                None,
                self.test_pos,
                self.test_neg,
                None,
                None,
                1,
                node_information,
                False,
                True
            )
        print('# test: %d' % (len(test_graphs)))
        self.test_graphs=test_graphs
    
    
    def getOmlaAttackAccuracy(self):
        #embeddings = generate_node2vec_embeddings(self.A,12)
        #node_information = embeddings
        Y=[]
        X=[]
        for graph in self.test_graphs:
            Y.append(int(graph.label))
            X.append(torch.sum(graph.node_features, dim=0).tolist())

        self.y=np.array(Y)
        self.x=np.array(X)
        scaler = StandardScaler()
        self.x= scaler.fit_transform(self.x)
        acc_test,_,_ = self.test_new()
        return acc_test,self.x,self.y
    
if __name__ == '__main__':
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    parser = argparse.ArgumentParser(description='Cluster Attack')
    parser.add_argument('--data', default=None, help='network name')
    parser.add_argument('--links', default=None, help='links name')
    parser.add_argument('--model', default=None, help='Model parent folder')
    args = parser.parse_args()
    
    #args.file_dir = os.path.dirname(os.path.realpath('__file__'))
    print(args.data)
    #exit(0)
    gcnEnc = OMLAEvaluator(args.data,args.links,args.model,device)
    gcnEnc.prepareData()
    accuracy,x,y = gcnEnc.getOmlaAttackAccuracy()
    _, F1 = dcm.F1(x, y)
    N1 = dcm.N1(x, y)
    # x,y = gcnEnc.processAndGenEmbeddings()
    # tsne = TSNE(n_components=2, verbose=1, random_state=123)
    # z = tsne.fit_transform(x)
    # df = pd.DataFrame()
    # df["y"] = y
    # df["comp-1"] = z[:,0]
    # df["comp-2"] = z[:,1]

    # #sns.scatterplot(x="comp-1", y="comp-2", hue=df.y.tolist(),
    # #                palette=sns.color_palette("hls", 2),
    # #                                data=df).set(title="Iris data T-SNE projection")
    # #plt.savefig('c3540_v8_sub3.png')
    # kmeans = KMeans(n_clusters=2)#, init='k-means++', max_iter=300, n_init=10, random_state=0)

    # X=z
    # pred_y = kmeans.fit_predict(X)

    # #clt_sim_matrix.fit(pred_y)
    # plt.scatter(X[:,0],X[:,1],c=df.y.tolist() )
    # plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1], s=300, c='red')
    # #plt.savefig('cluster_TSNE_'+str(args.file_name)+'.png')
    # index, F1 = dcm.F1(X, y)

    # print("F1:v1 "+str(F1))

    # num_correct = 0
    # for i in range(len(pred_y)):
    #     if pred_y[i] == y[i]:
    #         num_correct += 1
    # accuracy= (num_correct*100)/ len(y)
    print("Accuracy: {}, F1: {}, N1: {}".format(accuracy,F1,N1))