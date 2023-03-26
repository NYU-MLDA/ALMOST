import sys,os,re
#from scipy.optimize import dual_annealing
from dual_anneal import *
import time
import math,argparse,shutil
from utils import *

def main():
    parser = argparse.ArgumentParser(description='SA search')
    parser.add_argument('--benchmark', type=str, required=True,
                        help='Path of design AIG')
    parser.add_argument('--library', type=str, required=True,
                        help='Technology library path')
    parser.add_argument('--dumpdir', type=str, required=True,default="",
                        help='Main DUMP directory of benchmark to store result')
    parser.add_argument('--runID', type=str, required=True, default="0",
                        help='Run ID of SA run')
    parser.add_argument('--runs', type=int, required=False, default=1000,
                        help='Max. iterations')
    parser.add_argument('--metric', type=int, required=False, default=1,
                        help='optimization metric')
    parser.add_argument('--modeldir', type=str, required=False,default="",
                        help='Directory having pre-trained model and hyperparams')
    args = parser.parse_args()
    #seed_everything()

    origAIGPath = args.benchmark
    libraryPath = args.library
    rootDumpDir = args.dumpdir
    runID = args.runID
    max_iterations = args.runs
    optimization_metric = args.metric
    model_dir = args.modeldir
    if not (osp.exists(origAIGPath) and osp.exists(libraryPath)):
        print(origAIGPath)
        print("Incorrect path. Rerun")
        exit(0)
        
    if not osp.exists(model_dir):
        print("Warning: no pretrained model dir found.. Will encounter error later..")
        model_dir=None
     
    synthesizedAIGName = osp.splitext(osp.basename(origAIGPath))[0]+"_synthesized.v"
    runFolder = osp.join(rootDumpDir,'run'+str(runID))
    csvResultFile = osp.join(rootDumpDir,'data_run'+str(runID)+".csv") # Data to store area obtained in each iteration and best so far
    logFilePath = osp.join(runFolder,'log_run'+str(runID)+".log")   # Log data to dump area and read
    synthesizedAIGPath = osp.join(runFolder,"synthesized",synthesizedAIGName) # synthesized AIG path
    if not osp.exists(rootDumpDir):
        os.mkdir(rootDumpDir)
        
    if osp.exists(runFolder):
        shutil.rmtree(runFolder)
        
    os.mkdir(runFolder)
    os.mkdir(osp.join(runFolder,"synthesized"))
    
    
    lw = [0] * NUM_LENGTH_EPISODES
    up = [7] * NUM_LENGTH_EPISODES
    SetBaseline(origAIGPath,synthesizedAIGPath,libraryPath,logFilePath,csvResultFile,optimization_metric,model_dir)
    initialSynVec = [6,2,0,6,2,3,6,1,3,6] 
    
    starttime = time.time()
    ret = dual_annealing(simulateABCruns,args=({'Nfeval':0},),bounds=list(zip(lw, up)),no_local_search=True,maxfun=max_iterations,callback=evaluateStatus,initial_temp=400,x0=initialSynVec,visit=1.7,accept=-5000)
    endtime = time.time()
    timeElapsed = endtime-starttime
    print("\nBest solution reached\n")
    print(ret.fun)
    recipe=getRecipe(ret.x)
    print(recipe)
    # Generate best synthesized netlist (ALMOST synthesized in case of using adversarial model)
    synthesize(ret.x)
    print("\nTime elapsed: "+str(timeElapsed)+"s")
    
if __name__ == "__main__":
    main()
