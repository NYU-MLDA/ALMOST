import math
import os.path as osp
import os,re
from collections import OrderedDict
import numpy as np
import pickle
import pandas as pd
import random,torch,shutil
from models.graphcnn import GraphCNN
from dual_anneal import *
from abcUtilities import simulateABCruns,getSynthesisCmd
from util_functions import getSecretKey,sanityCheckPath

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
LIBRARY_FILE="/home/abc586/currentResearch/ML_locking/lib/nangate45.lib"
# 1- ADP only
# 2- ADP+F1
# 3- ADP+N1
# 4- F1 only
# 5- N1 only

  
class SAHandler:
    def __init__(self,validDataLockFile,library,dumpDir,preTrainedModelPath=None,classifier=None,max_iterations=100):
        self.preTrainedModelPath = preTrainedModelPath
        self.origAIGPath = validDataLockFile
        self.lib = library
        self.dumpDir = dumpDir
        self.NUM_LENGTH_EPISODES = 10
        self.classifier = classifier
        self.max_iterations=max_iterations
        
        ## Sanity Checks
        if not self.preTrainedModelPath == None:
            sanityCheckPath(self.preTrainedModelPath)
        sanityCheckPath(self.origAIGPath)
        sanityCheckPath(self.lib)
        if not osp.exists(self.dumpDir):
            os.mkdir(self.dumpDir)
            
        self.synthesizedAIG = osp.splitext(osp.basename(self.origAIGPath))[0]+"_synthesized.v"
        self.synthesizedAIGPath = osp.join(self.dumpDir,self.synthesizedAIG)
        self.logFile=osp.join(self.dumpDir,"log.txt")
        self.secret_key = getSecretKey(self.origAIGPath)
        self.lw = [0] * self.NUM_LENGTH_EPISODES
        self.up = [7] * self.NUM_LENGTH_EPISODES
        
    def loadPreTrainedModel(self,node_feature_shape,device):
        num_classes=2
        sanityCheckPath(osp.join(self.preTrainedModelPath,'model_hyper.pkl'))
        sanityCheckPath(osp.join(self.preTrainedModelPath,'model_model.pth'))
        with open(osp.join(self.preTrainedModelPath,'model_hyper.pkl'),'rb') as hyperparameters_name:
            saved_args = pickle.load(hyperparameters_name)
        argsDict = {}
        for key, value in vars(saved_args).items(): # replace with saved cmd_args
            argsDict[key] = value
        classifier = GraphCNN(argsDict['num_layers'], argsDict['num_mlp_layers'],node_feature_shape,argsDict['hidden_dim'], num_classes, argsDict['final_dropout'], \
            argsDict['learn_eps'], argsDict['graph_pooling_type'], argsDict['neighbor_pooling_type'], device).to(device)
        if torch.cuda.is_available():
            classifier = classifier.cuda()
        model_name = osp.join(self.preTrainedModelPath,'model_model.pth')
        classifier.load_state_dict(torch.load(model_name))
        self.classifier = classifier
        
    def runSimulatedAnnealingAttack(self):
        if self.classifier == None:
            self.loadPreTrainedModel(19,'cuda') # Sneaky and dirty way
        initialSynVec = [6,2,0,6,2,3,6,1,3,6]
        ret = dual_annealing(simulateABCruns,args=({'origAIG':self.origAIGPath,'synthAIG':self.synthesizedAIGPath,'lib':self.lib,'log':self.logFile,'key':self.secret_key,'ptModel':self.classifier},), \
                bounds=list(zip(self.lw,self.up)),no_local_search=True,maxfun=self.max_iterations,initial_temp=500,x0=initialSynVec,visit=1.7,accept=-5000)
        synthesisCmd = getSynthesisCmd(ret.x)
        return synthesisCmd  