import os.path as osp
import os

DESIGN_LIST=["c6288"]
KEYSIZE = 128
NUM_TRAIN_DATA=900
NUM_VALID_DATA=100
LIBRARY_FILE="/home/abc586/currentResearch/ML_locking/lib/nangate45.lib"
## First resynthesize using resyn2
#RESYN2_CMD =  "balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance;"
#RESYN2_CMD="balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance;refactor;balance;resub -z;balance;rewrite;resub;resub;resub;refactor -z;balance;"
#RESYN2_CMD_c5315="resub -z;resub;refactor -z;rewrite -z;refactor -z;refactor;resub -z;resub -z;rewrite;balance;" #C5315
#RESYN2_CMD="resub;refactor -z;refactor;refactor -z;refactor;refactor -z;resub;rewrite -z;resub -z;refactor -z;" #C1355
#RESYN2_CMD="refactor;refactor -z;resub -z;balance;resub -z;balance;refactor -z;refactor -z;resub -z;rewrite;" #C1908
#RESYN2_CMD="resub;resub;refactor;resub -z;refactor;rewrite;refactor -z;refactor;refactor -z;resub -z;" #C2670
#RESYN2_CMD="balance;refactor -z;rewrite -z;refactor -z;rewrite -z;refactor -z;resub -z;refactor;rewrite;balance;" #C3540
#RESYN2_CMD="rewrite -z;refactor -z;rewrite -z;balance;refactor;refactor -z;refactor -z;rewrite -z;resub -z;refactor;" #C7552
RESYN2_CMD="refactor -z;refactor;rewrite;refactor -z;refactor;refactor -z;refactor -z;rewrite -z;rewrite -z;refactor;" #C6288

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

def synthesize(mappedVerilogFile,outputVerilogFile):
    synthesisCmd = "yosys-abc -c \"read_lib "+LIBRARY_FILE+"; read -m "+mappedVerilogFile+";strash;"+RESYN2_CMD+"map;topo; write_verilog "+outputVerilogFile+";stime\""
    os.system(synthesisCmd)
    
def relockCircuit(origLockedDesign,outputRelockedDesign,folderName):
    perlCmd = "perl RLL_self_referencing.pl -a 4 -lib 45 -k "+str(KEYSIZE)+" -i "+origLockedDesign+" -o "+folderName+" -f "+outputRelockedDesign
    print(perlCmd)
    os.system(perlCmd)
    
for d in DESIGN_LIST:
    origFile = osp.join(d,"locked_"+d+"_k64_orig.v")
    key64Bit = getSecretKey(origFile)
    resyn2File = osp.join(d,"Test_"+d+"_k64_resyn.v")
    synthesize(origFile,resyn2File)
    line_prepender(resyn2File,key64Bit)
    # for i in range(NUM_TRAIN_DATA):
    #     outputFile = "Train_"+d+"_syn_locked_rnd64_relocked_k"+str(KEYSIZE)+"_"+str(i)+".v"
    #     relockCircuit(resyn2File,outputFile,d)
    #     outputFile = osp.join(d,outputFile)
    #     key128Bit = getSecretKey(outputFile)
    #     synthesize(outputFile,outputFile)
    #     line_prepender(outputFile,key128Bit)
    # for i in range(NUM_VALID_DATA):
    #     outputFile = "Valid_"+d+"_syn_locked_rnd64_relocked_k"+str(KEYSIZE)+"_"+str(i)+".v"
    #     relockCircuit(resyn2File,outputFile,d)
    #     outputFile = osp.join(d,outputFile)
    #     synthesize(outputFile,outputFile)