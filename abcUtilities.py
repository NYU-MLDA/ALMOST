
import math
from evaluator import OMLAEvaluator
from util_functions import line_prepender

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


def getSynthesisCmd(synthesisVec):
    synthesisCmd = ""
    for i in synthesisVec:
        synthesisCmd += (synthesisOpToPosDic[int(math.floor(i))]+";")
    return synthesisCmd
           
def synthesize(synthesisVec,files):
    synthesisCmd = getSynthesisCmd(synthesisVec)
    abcRunCmd = "yosys-abc -c \"read_lib "+files['lib']+"; read -m "+files['origAIG']+";strash;"+synthesisCmd+"map;topo; write_verilog "+files['synthAIG']+";stime \" > "+files['log']+" 2>&1"
    os.system(abcRunCmd)
          
def synthesizeAndGetADP(synthesisVec,files):
    synthesize(synthesisVec,files)
    with open(files['log'],'r') as f:
        adpInformation = re.findall('[a-zA-Z0-9.]+',f.readlines()[-1])
        area = float(adpInformation[-9])
        time = float(adpInformation[-4])
        return area,time
 
def getSecurityScoresFromOmlaAttack(files):
    cktprefix = osp.splitext(osp.basename(files['origAIG']))[0]
    synthesizedAIGFolder = os.path.dirname(files['synthAIG'])
    clusterDataFolder = osp.join(os.path.dirname(synthesizedAIGFolder),cktprefix+"_cluster")
    if osp.exists(clusterDataFolder):
        shutil.rmtree(clusterDataFolder)
    line_prepender(files['synthAIG'],files['key'])
    perlCmd = "perl netlist_to_subgraphs_cluster_version.pl -f "+clusterDataFolder+" -i "+ \
        synthesizedAIGFolder+" > "+osp.join(os.path.dirname(synthesizedAIGFolder),"log_"+cktprefix+"_cluster.txt")
    returnCode = os.system(perlCmd)
    print(perlCmd,returnCode)
    omlaEvalObj = OMLAEvaluator(clusterDataFolder,"link.txt",files['ptModel'],device=device)
    omlaEvalObj.prepareData()
    acc,xFeature,yLabel = omlaEvalObj.getOmlaAttackAccuracy()
    origF1,origN1 = getOrigMetrics(xFeature,yLabel)
    pcaF1,pcaN1 = getPCAMetrics(xFeature,yLabel)
    tsneF1,tsneN1 = getTSNEMetrics(xFeature,yLabel)
    return acc,[origF1,pcaF1,tsneF1],[origN1,pcaN1,tsneN1]
     

def simulateABCruns(x,files):
    area,time = synthesizeAndGetADP(x,files)
    acc,f1Scores,n1Scores = getSecurityScoresFromOmlaAttack(files)
    return abs(acc-0.5)