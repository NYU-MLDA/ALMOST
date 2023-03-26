import math
import os.path as osp
import os,re
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from numpy import reshape
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from dcm import dcm
import pickle
import pandas as pd
from GCNEncoding import GCNEncoder
import random,torch,shutil
from models.graphcnn import GraphCNN

LIBRARY_FILE = None
LOG_FILE = None
NUM_LENGTH_EPISODES = 10
RESYN2_AREA = 0
RESYN_TIME = 0
RESYN2_ORIGF1 = 0.0
RESYN2_ORIGN1 = 0.0
RESYN2_ORIGACC = 0.0
GLOBAL_AIG = None
GLOBAL_FILE_HANDLER = None
BEST_ADP_RATIO = 1
GLOBAL_AIG_SYNTHESIZED = None
SECRET_KEY_LINE = None
OPTIMIZATION_METRIC = 1
PRETRAINED_MODEL_FOLDER=None
device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
# 1- ADP only
# 2- ADP+F1
# 3- ADP+N1
# 4- F1 only
# 5- N1 only

resyn2Cmd =  "balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance;"
len20SynthesisCmd = resyn2Cmd

 

synthesisOpToPosDic = \
{
     0: "refactor",
     1: "refactor -z",
     2: "rewrite",
     3: "rewrite -z",
     4: "resub",
     5: "resub -z",
     6: "balance"
}

#gate encoding
l_n={
"XOR": "10000000000000",
"XNOR":"01000000000000",
"AND": "00100000000000",
"OR":"00010000000000",
"NAND":"00001000000000",
"NOR": "00000100000000",
"NONE":"00000010000000",
"AOI": "00000001000000",
"INV": "00000000100000",
"OAI": "00000000010000",
"KI":  "00000000001000",
"PI":  "00000000000100",
"PO":  "00000000000010",
"MUX": "00000000000001"
}

def seed_everything(seed=566):                                                 
    random.seed(seed)
    #torch.seed(seed)
    #torch.use_deterministic_algorithms(True)                                                 
    torch.manual_seed(seed)
    np.random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)                                                   
        torch.cuda.manual_seed_all(seed)                                             
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        

        
def getSecretKey(origLockedFile):
    with open(origLockedFile,'r') as f:
        lines = f.readlines()
    keyLine = lines[0] # Can be dangerous if the secret key is not dumped in first line
    return keyLine
        
def SetBaseline(origAIG,synthesizedAIGPath,libraryFile,logFile,dumpDataFile,optimization_metric,model_folder_path=None):
    global RESYN2_AREA,LIBRARY_FILE,LOG_FILE,GLOBAL_FILE_HANDLER,GLOBAL_AIG,RESYN2_TIME,GLOBAL_AIG_SYNTHESIZED
    global OPTIMIZATION_METRIC,RESYN2_ORIGF1,RESYN2_ORIGN1,SECRET_KEY_LINE,RESYN2_ORIGACC,PRETRAINED_MODEL_FOLDER
    LIBRARY_FILE = libraryFile
    LOG_FILE = logFile
    GLOBAL_AIG = origAIG
    GLOBAL_AIG_SYNTHESIZED = synthesizedAIGPath
    PRETRAINED_MODEL_FOLDER = model_folder_path
    GLOBAL_FILE_HANDLER = open(dumpDataFile,'w')
    OPTIMIZATION_METRIC=optimization_metric
    abcRunCmd = "yosys-abc -c \"read_lib "+LIBRARY_FILE+"; read -m "+GLOBAL_AIG+";strash;"+len20SynthesisCmd+"map;topo; write_verilog "+GLOBAL_AIG_SYNTHESIZED+";stime \" > "+LOG_FILE+" 2>&1"
    os.system(abcRunCmd)
    with open(LOG_FILE,'r') as f:
        areaTimingInformation = re.findall('[a-zA-Z0-9.]+',f.readlines()[-1])
        RESYN2_AREA = float(areaTimingInformation[-9])
        RESYN2_TIME = float(areaTimingInformation[-4])
    SECRET_KEY_LINE = getSecretKey(GLOBAL_AIG)
    #f1Scores,n1Scores = getSecurityScoresFromGCNEncoding()#getSecurityScores()
    acc,f1Scores,n1Scores = getSecurityScoresFromOmlaAttack()
    RESYN2_ORIGACC = acc
    RESYN2_ORIGN1 = n1Scores[0]
    RESYN2_ORIGF1 = f1Scores[0]

def synthesize(synthesisVec):
    synthesisCmd = ""
    for i in synthesisVec:
        synthesisCmd += (synthesisOpToPosDic[int(math.floor(i))]+";")
    abcRunCmd = "yosys-abc -c \"read_lib "+LIBRARY_FILE+"; read -m "+GLOBAL_AIG+";strash;"+synthesisCmd+"map;topo; write_verilog "+GLOBAL_AIG_SYNTHESIZED+";stime \" > "+LOG_FILE+" 2>&1"
    os.system(abcRunCmd)
          
def synthesizeAndGetADP(synthesisVec):
    synthesize(synthesisVec)
    with open(LOG_FILE,'r') as f:
        adpInformation = re.findall('[a-zA-Z0-9.]+',f.readlines()[-1])
        area = float(adpInformation[-9])
        time = float(adpInformation[-4])
        return area,time
 
def extractSubgraphEncoding(file_name,locked_file_name):
    X=[]
    Y=[]
    with open(locked_file_name, "r") as file:
         first_line = file.readline()
    result=re.search("\/\/Secret key is\'(.*)\'.*",first_line)
    mystr=result.group(1).replace(' ','')
    secret_key=np.array(list(mystr),dtype=int)
    with open(file_name) as file:
        lines = file.readlines()
    key_size=-1
    for line in lines:
        if "start$" in line:
            key_size=key_size+1
        elif "end$" not in line:
            #print(line)
            X_small=[]
            line=line.rstrip().split()
            for word in line:
                encoding=l_n.get(word)
                #print(encoding)
                for code in encoding:
                    X_small.append(int(code))
            X.append(X_small)
            Y.append(secret_key[key_size])
    x=np.array(X)
    y=np.array(Y)
    scaler = StandardScaler()
    x= scaler.fit_transform(x)
    return x,y

def getOrigMetrics(x,y):
    _, F1 = dcm.F1(x, y)
    N1 = dcm.N1(x, y)
    return F1,N1
     
def getPCAMetrics(x,y):
    pca = PCA(n_components=2)
    principalComponents = pca.fit_transform(x)
    principalDf = pd.DataFrame(data = principalComponents
                , columns = ['principal component 1', 'principal component 2'])
    PCA_X=np.empty([len(y),2])
    PCA_X[:,1]=principalDf["principal component 2"].values
    PCA_X[:,0]=principalDf["principal component 1"].values
    _,F1 = dcm.F1(PCA_X, y)
    N1 = dcm.N1(PCA_X, y)
    return F1,N1
    
def getTSNEMetrics(x,y):
    tsne = TSNE(n_components=2, verbose=0, random_state=123)
    z = tsne.fit_transform(x)
    _, F1 = dcm.F1(z, y)
    N1 = dcm.N1(z, y)
    return F1,N1

def line_prepender(filename, keyContent):
    with open(filename, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(keyContent.rstrip('\r\n') + '\n' + content)
        
def getSecurityScoresFromNaiveEncoding():
    cktprefix = osp.splitext(osp.basename(GLOBAL_AIG))[0]
    xFeatureFile = osp.join(os.getcwd(),'subgraphs_sub3','64','XOR',cktprefix,cktprefix+"_v1.txt")
    if osp.exists(xFeatureFile):
        os.remove(xFeatureFile)
    perlCmd = "perl get_subgraphs_levels_full.pl  -i "+GLOBAL_AIG_SYNTHESIZED+" -p "+os.getcwd()+" -k 64 -lock XOR -folder "+cktprefix+" -trial 1"
    returnCode = os.system(perlCmd)
    print(perlCmd,returnCode)
    xFeature,yLabel = extractSubgraphEncoding(xFeatureFile,GLOBAL_AIG)
    origF1,origN1 = getOrigMetrics(xFeature,yLabel)
    pcaF1,pcaN1 = getPCAMetrics(xFeature,yLabel)
    tsneF1,tsneN1 = getTSNEMetrics(xFeature,yLabel)
    return [origF1,pcaF1,tsneF1],[origN1,pcaN1,tsneN1]


def getSecurityScoresFromGCNEncoding():
    cktprefix = osp.splitext(osp.basename(GLOBAL_AIG))[0]
    synthesizedAIGFolder = os.path.dirname(GLOBAL_AIG_SYNTHESIZED)
    clusterDataFolder = osp.join(os.path.dirname(synthesizedAIGFolder),cktprefix+"_cluster")
    if osp.exists(clusterDataFolder):
        shutil.rmtree(clusterDataFolder)
    line_prepender(GLOBAL_AIG_SYNTHESIZED,SECRET_KEY_LINE)
    perlCmd = "perl netlist_to_subgraphs_cluster_version.pl -f "+clusterDataFolder+" -i "+ \
        synthesizedAIGFolder+" > "+osp.join(os.path.dirname(synthesizedAIGFolder),"log_"+cktprefix+"_cluster.txt")
    returnCode = os.system(perlCmd)
    print(perlCmd,returnCode)
    gcnEnc = GCNEncoder(clusterDataFolder,"link.txt")
    gcnEnc.prepareData()
    xFeature,yLabel = gcnEnc.processAndGenEmbeddings()
    origF1,origN1 = getOrigMetrics(xFeature,yLabel)
    pcaF1,pcaN1 = getPCAMetrics(xFeature,yLabel)
    tsneF1,tsneN1 = getTSNEMetrics(xFeature,yLabel)
    return [origF1,pcaF1,tsneF1],[origN1,pcaN1,tsneN1]

def getSecurityScoresFromOmlaAttack():
    cktprefix = osp.splitext(osp.basename(GLOBAL_AIG))[0]
    synthesizedAIGFolder = os.path.dirname(GLOBAL_AIG_SYNTHESIZED)
    clusterDataFolder = osp.join(os.path.dirname(synthesizedAIGFolder),cktprefix+"_cluster")
    if osp.exists(clusterDataFolder):
        shutil.rmtree(clusterDataFolder)
    line_prepender(GLOBAL_AIG_SYNTHESIZED,SECRET_KEY_LINE)
    perlCmd = "perl netlist_to_subgraphs_cluster_version.pl -f "+clusterDataFolder+" -i "+ \
        synthesizedAIGFolder+" > "+osp.join(os.path.dirname(synthesizedAIGFolder),"log_"+cktprefix+"_cluster.txt")
    returnCode = os.system(perlCmd)
    print(perlCmd,returnCode)
    gcnEnc = GCNEncoder(clusterDataFolder,"link.txt",PRETRAINED_MODEL_FOLDER,device=device)
    gcnEnc.prepareData()
    acc,xFeature,yLabel = gcnEnc.getOmlaAttackAccuracy()
    origF1,origN1 = getOrigMetrics(xFeature,yLabel)
    pcaF1,pcaN1 = getPCAMetrics(xFeature,yLabel)
    tsneF1,tsneN1 = getTSNEMetrics(xFeature,yLabel)
    return acc,[origF1,pcaF1,tsneF1],[origN1,pcaN1,tsneN1]
    
    
    
def evaluateStatus(cur_f,cur_x,best_f,best_x):
    area,time = synthesizeAndGetADP(cur_x)
    #f1Scores,n1Scores = getSecurityScoresFromGCNEncoding()
    acc,f1Scores,n1Scores = getSecurityScoresFromOmlaAttack()
    curADPRatio = (RESYN2_AREA*RESYN2_TIME)/(area*time)
    f1SecurityRatio = f1Scores[0]/RESYN2_ORIGF1
    n1SecurityRatio = n1Scores[0]/RESYN2_ORIGN1
    accRatio = acc/RESYN2_ORIGACC
    GLOBAL_FILE_HANDLER.write(str(curADPRatio)+","+str(f1SecurityRatio)+","+str(n1SecurityRatio)+",")
    GLOBAL_FILE_HANDLER.write(str(accRatio)+","+str(acc))
    for i in range(len(f1Scores)):
        GLOBAL_FILE_HANDLER.write(","+str(f1Scores[i])+","+str(n1Scores[i]))
    for i in cur_x:
        GLOBAL_FILE_HANDLER.write(","+synthesisOpToPosDic[int(math.floor(i))])
    GLOBAL_FILE_HANDLER.write("\n")
    print('Current vector:',cur_x)
    print('Current energy:',cur_f)
    return False

def getRecipe(recipeVec):
    advGenRecipe= ""
    for i in recipeVec:
        advGenRecipe+","+synthesisOpToPosDic[int(math.floor(i))]
    return advGenRecipe

def simulateABCruns(x,info):
    area,time = synthesizeAndGetADP(x)
    #f1Scores,n1Scores = getSecurityScores()
    acc,f1Scores,n1Scores = getSecurityScoresFromOmlaAttack()
    #if info['Nfeval'] % 10 == 0:
    #    print('Iter:' + str(info['Nfeval']) + ", Area: " + str(area) +" Delay: "+str(time),flush=True)
    info["Nfeval"] += 1
    # Cost function for optimization
    if OPTIMIZATION_METRIC == 1:
        return (area*time)/(RESYN2_AREA*RESYN2_TIME)
    elif OPTIMIZATION_METRIC == 2:
        return (area*time)/(RESYN2_AREA*RESYN2_TIME*f1Scores[0])
    elif OPTIMIZATION_METRIC == 3:
        return (area*time)/(RESYN2_AREA*RESYN2_TIME*n1Scores[0])
    elif OPTIMIZATION_METRIC == 4:
        return 1/f1Scores[0]
    elif OPTIMIZATION_METRIC == 5:
        return 1/n1Scores[0]
    elif OPTIMIZATION_METRIC == 6:
        return abs(acc-0.5)
