import os.path as osp
import os
import numpy as np
import shutil

DESIGN_LIST=["c1355"]
REPOS_HOME="/home/abc586/currentResearch/ALMOST_final"
LOCKED_NETLIST_FOLDER=osp.join(REPOS_HOME,"locked_netlists")
KEYSIZE = 128
NUM_TRAIN_DATA=900
NUM_VALID_DATA=100
LIBRARY_FILE="/home/abc586/currentResearch/ML_locking/lib/nangate45.lib"



## First resynthesize using resyn2
RESYN2_CMD =  "balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance;"

RANDOM_RECIPES = {
    0: "rewrite -z; refactor -z; rewrite -z; resub; resub -z; refactor -z; rewrite -z; balance; rewrite; rewrite -z;",
    1: "resub; resub -z; refactor -z; rewrite -z; balance; rewrite; rewrite -z;rewrite -z; refactor -z; rewrite -z; ",
    2: "resub; resub -z;  rewrite; rewrite -z;rewrite -z; refactor -z; rewrite -z; refactor -z; rewrite -z; balance;",
    3: "refactor -z; rewrite -z; balance; rewrite; rewrite -z; refactor -z; rewrite -z; resub; resub -z;  rewrite -z;",
    4: "refactor -z; rewrite -z; refactor -z; rewrite -z; resub; resub -z;rewrite -z; balance; rewrite;   rewrite -z;",
    5: "refactor -z;  resub -z;rewrite -z; balance; rewrite; rewrite -z; refactor -z; rewrite -z; resub;   rewrite -z;",
    6: "refactor; balance; rewrite; rewrite -z; balance; refactor -z; balance; rewrite;  rewrite -z; balance;",
    7: "refactor;refactor -z; balance; rewrite;  rewrite -z; balance; balance; rewrite; rewrite -z; balance; ",
    8: "rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance; rewrite; refactor; balance;  balance;",
    9: "refactor; rewrite -z; balance; rewrite; balance; resub;  balance; refactor -z; resub -z; balance;"
}
#RESYN2_CMD="refactor;balance;resub -z;balance;rewrite;resub;resub;resub;refactor -z;balance;"

def getSecretKey(origLockedFile):
    with open(origLockedFile,'r') as f:
        lines = f.readlines()
    keyLine = lines[0] # Can be dangerous if the secret key is not dumped in first line
    return keyLine

def line_prepender(filename, keyContent):
    with open(filename, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(keyContent.rstrip('\r\n') + '\n' + content)

def synthesize(mappedVerilogFile,outputVerilogFile,recipe):
    synthesisCmd = "yosys-abc -c \"read_lib "+LIBRARY_FILE+"; read -m "+mappedVerilogFile+";strash;"+recipe+"map;topo; write_verilog "+outputVerilogFile+";stime\""
    os.system(synthesisCmd)
    
def relockCircuit(origLockedDesign,outputRelockedDesign,folderName):
    perlCmd = "perl RLL_self_referencing.pl -a 4 -lib 45 -k "+str(KEYSIZE)+" -i "+origLockedDesign+" -o "+folderName+" -f "+outputRelockedDesign
    print(perlCmd)
    os.system(perlCmd)
    
for d in DESIGN_LIST:
    lockedNetlist=osp.join(LOCKED_NETLIST_FOLDER,d,"locked_"+d+"_k64_orig.v")
    relockedFolder = osp.join(d+"_resynRelocked")
    if not osp.exists(relockedFolder):
        os.mkdir(relockedFolder)
    shutil.copy(lockedNetlist,relockedFolder)
    origFile = osp.join(relockedFolder,"locked_"+d+"_k64_orig.v")
    key64Bit = getSecretKey(origFile)
    resyn2File = osp.join(relockedFolder,"Test_"+d+"_k64_resyn.v")
    synthesize(origFile,resyn2File,RESYN2_CMD)
    line_prepender(resyn2File,key64Bit)
    resyn2Folder = osp.join(d+"_resynRelockedRandomSyn")
    randomFolder = osp.join(d+"_resynRelockedResyn")
    shutil.copy(resyn2File,resyn2Folder)
    shutil.copy(resyn2File,randomFolder)
    if not osp.exists(resyn2Folder):
        os.mkdir(resyn2Folder)
    if not osp.exists(randomFolder):
        os.mkdir(randomFolder)
    for i in range(NUM_TRAIN_DATA):
        outputFileName = "Train_"+d+"_syn_locked_rnd64_relocked_k"+str(KEYSIZE)+"_"+str(i)+".v"
        outputFile = osp.join(relockedFolder,outputFileName)
        relockCircuit(resyn2File,outputFileName,relockedFolder)
        outputFile2 = osp.join(resyn2Folder,outputFileName)
        outputFile3 = osp.join(randomFolder,outputFileName)
        key128Bit = getSecretKey(outputFile)
        synthesize(outputFile,outputFile2,RESYN2_CMD)
        randomSynRecipe = RANDOM_RECIPES[np.random.randint(0,10)]
        synthesize(outputFile,outputFile3,randomSynRecipe)
        line_prepender(outputFile2,key128Bit)
        line_prepender(outputFile3,key128Bit)
    for i in range(NUM_VALID_DATA):
        outputFileName = "Valid_"+d+"_syn_locked_rnd64_relocked_k"+str(KEYSIZE)+"_"+str(i)+".v"
        outputFile = osp.join(relockedFolder,outputFileName)
        relockCircuit(resyn2File,outputFileName,relockedFolder)
        key128Bit = getSecretKey(outputFile)
        outputFile2= osp.join(resyn2Folder,outputFileName)
        synthesize(outputFile,outputFile2,RESYN2_CMD)
        outputFile3 = osp.join(randomFolder,outputFileName)
        randomSynRecipe = RANDOM_RECIPES[np.random.randint(0,10)]
        synthesize(outputFile,outputFile3,randomSynRecipe)
        line_prepender(outputFile2,key128Bit)
        line_prepender(outputFile3,key128Bit)