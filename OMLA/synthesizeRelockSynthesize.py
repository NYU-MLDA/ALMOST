import os.path as osp
import os

DESIGN_LIST=["c5315"]
KEYSIZE = 128
NUM_TRAIN_DATA=200
NUM_VALID_DATA=1
LIBRARY_FILE="/home/abc586/currentResearch/ML_locking/lib/nangate45.lib"
## First resynthesize using resyn2
RESYN2_CMD =  "balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance;"
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

def synthesize(mappedVerilogFile,outputVerilogFile):
    synthesisCmd = "yosys-abc -c \"read_lib "+LIBRARY_FILE+"; read -m "+mappedVerilogFile+";strash;"+RESYN2_CMD+"map;topo; write_verilog "+outputVerilogFile+";stime\""
    os.system(synthesisCmd)
    
def relockCircuit(origLockedDesign,outputRelockedDesign,folderName):
    perlCmd = "perl RLL_self_referencing.pl -a 4 -lib 45 -k "+str(KEYSIZE)+" -i "+origLockedDesign+" -o "+folderName+" -f "+outputRelockedDesign
    print(perlCmd)
    os.system(perlCmd)
    
for d in DESIGN_LIST:
    origFile = osp.join(d+"_relocked","locked_"+d+"_k64_orig.v")
    key64Bit = getSecretKey(origFile)
    resyn2File = osp.join(d+"_relocked","Test_"+d+"_k64_resyn.v")
    synthesize(origFile,resyn2File)
    line_prepender(resyn2File,key64Bit)
    for i in range(NUM_TRAIN_DATA):
        outputFileName = "Train_"+d+"_syn_locked_rnd64_relocked_k"+str(KEYSIZE)+"_"+str(i)+".v"
        outputFile = osp.join(d+"_relocked",outputFileName)
        relockCircuit(resyn2File,outputFileName,d+"_relocked")
        outputFile2 = osp.join(d+"_relockedSynthesized",outputFileName)
        key128Bit = getSecretKey(outputFile)
        synthesize(outputFile,outputFile2)
        line_prepender(outputFile2,key128Bit)
    for i in range(NUM_VALID_DATA):
        outputFileName = "Valid_"+d+"_syn_locked_rnd64_relocked_k"+str(KEYSIZE)+"_"+str(i)+".v"
        outputFile = osp.join(d+"_relocked",outputFileName)
        relockCircuit(resyn2File,outputFileName,d+"_relocked")
        key128Bit = getSecretKey(outputFile)
        outputFile2= osp.join(d+"_relockedSynthesized",outputFileName)
        synthesize(outputFile,outputFile2)
        line_prepender(outputFile2,key128Bit)