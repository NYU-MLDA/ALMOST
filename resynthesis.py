import os.path as osp
import os
from util_functions import getSecretKey,line_prepender
import glob,shutil

LIBRARY_FILE="/home/abc586/currentResearch/ML_locking/lib/nangate45.lib"
## First resynthesize using resyn2
#RESYN2_CMD =  "balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance;"
#RESYN2_CMD="refactor;balance;resub -z;balance;rewrite;resub;resub;resub;refactor -z;balance;"


def synthesizeDesign(library,synRecipe,mappedVerilogFile,outputVerilogFile):
    synthesisCmd = "yosys-abc -c \"read_lib "+library+"; read -m "+mappedVerilogFile+";strash;"+synRecipe+";map;topo; write_verilog "+outputVerilogFile+"\""
    os.system(synthesisCmd)
    
class Resynthesizer:
    def __init__(self,designName,library,synRecipe,synID,origRelockedFileLoc,trainTestFileDestination,dataFolder,keySize=128):
        self.designName = designName
        self.keySize = keySize
        self.synRecipe = synRecipe
        self.synID = synID
        self.dataFolder = dataFolder
        self.lib=library
        self.trainFiles = glob.glob(osp.join(origRelockedFileLoc,"Train*"))[:100]
        self.validFiles = glob.glob(osp.join(origRelockedFileLoc,"Valid*"))[:20]
        self.trnTstFilePath = trainTestFileDestination
        
    def synthesizeFiles(self,fileList,dataTypeKeyword):
        for idx in range(len(fileList)):
            outputFile = osp.join(self.trnTstFilePath,dataTypeKeyword+"_"+self.designName+"_syn"+str(self.synID)+"_locked_rnd64_relocked_k"+str(self.keySize)+"_"+str(idx)+".v")
            key = getSecretKey(fileList[idx])
            synthesizeDesign(self.lib,self.synRecipe,fileList[idx],outputFile)
            line_prepender(outputFile,key)
        
    def augmentNewData(self):
        self.synthesizeFiles(self.trainFiles,"Train")
        self.synthesizeFiles(self.validFiles,"Valid")
        if osp.exists(self.dataFolder):
            shutil.rmtree(self.dataFolder)
        os.mkdir(self.dataFolder)
        perlCmd = "perl netlist_to_subgraphs_cluster_version.pl -f "+self.dataFolder+" -i "+ \
          self.trnTstFilePath+" > "+osp.join(self.dataFolder,"log_"+self.designName+"_"+str(self.synID)+"_cluster.txt")
        print(perlCmd)
        returnCode = os.system(perlCmd)
        print("Return code:"+str(returnCode))