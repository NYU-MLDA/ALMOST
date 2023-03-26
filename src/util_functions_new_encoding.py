from __future__ import print_function
import numpy as np
import random
from tqdm import tqdm
import os, sys, pdb, math, time
import networkx as nx
import argparse
import scipy.io as sio
import scipy.sparse as ssp
from sklearn import metrics
from gensim.models import Word2Vec
import warnings
warnings.simplefilter('ignore', ssp.SparseEfficiencyWarning)
cur_dir = os.path.dirname(os.path.realpath(__file__))
#sys.path.append('%s/../../pytorch_DGCNN' % cur_dir)
sys.path.append('%s/software/node2vec/src' % cur_dir)
#from util import S2VGraph
from util import S2VGraph
import node2vec
import multiprocessing as mp
from itertools import islice

def sample_neg(net, test_ratio=0.1, train_pos=None, test_pos=None, max_train_num=None,
               all_unknown_as_negative=False):
    # get upper triangular matrix
    net_triu = ssp.triu(net, k=1)
    # sample positive links for train/test
    row, col, _ = ssp.find(net_triu)
    # sample positive links if not specified
    # if max_train_num is set, randomly sample train links
    # sample negative links for train/test
    train_num = len(train_pos[0]) if train_pos else 0
    test_num = len(test_pos[0]) if test_pos else 0
    neg = ([], [])
    n = net.shape[0]
    #print('sampling negative links for train and test')
    if  all_unknown_as_negative:
        # regard all unknown links as test_negs, sample a portion from them as train_negs
        while len(neg[0]) < train_num:
            i, j = random.randint(0, n-1), random.randint(0, n-1)
            if i < j and net[i, j] == 0:
                neg[0].append(i)
                neg[1].append(j)
            else:
                continue
        train_neg  = (neg[0], neg[1])
        test_neg_i, test_neg_j, _ = ssp.find(ssp.triu(net==0, k=1))
        test_neg = (test_neg_i.tolist(), test_neg_j.tolist())
    return train_pos, train_neg, test_pos, test_neg


def links2subgraphs(A,B, train_pos, train_neg, test_pos, test_neg, val_pos,val_neg, h=1,
                    max_nodes_per_hop=None, node_information=None, no_parallel=False, DE_FLAG=True):
    # automatically select h from {1, 2}
    if h == 'auto': #TODO modify auto later
        # split train into val_train and val_test
        _, _, val_test_pos, val_test_neg = sample_neg(A, 0.1)
        val_A = A.copy()
        val_A[val_test_pos[0], val_test_pos[1]] = 0
        val_A[val_test_pos[1], val_test_pos[0]] = 0
        val_auc_CN = CN(val_A, val_test_pos, val_test_neg)
        val_auc_AA = AA(val_A, val_test_pos, val_test_neg)
        print('\033[91mValidation AUC of AA is {}, CN is {}\033[0m'.format(
            val_auc_AA, val_auc_CN))
        if val_auc_AA >= val_auc_CN:
            h = 2
            print('\033[91mChoose h=2\033[0m')
        else:
            h = 1
            print('\033[91mChoose h=1\033[0m')

    # extract enclosing subgraphs
    #max_n_label = {'value': 0}
    def helper(A,B, links, g_label, DE_FLAG=True):
        g_list = []
        if no_parallel:
            #print("Am I here?")
            for i in tqdm(links):
                g, n_labels, n_features,ind = subgraph_extraction_labeling(i, A, B,h, max_nodes_per_hop, node_information, DE_FLAG)
     #           max_n_label['value'] = max(max(n_labels), max_n_label['value'])
                g_list.append(S2VGraph(g, g_label, n_labels, n_features,i))
            return g_list
        else:
            # the parallel extraction code
            start = time.time()
            pool = mp.Pool(mp.cpu_count())
            results = pool.map_async(
                parallel_worker,
                [(i, A,B, h, max_nodes_per_hop, node_information, DE_FLAG) for i in links]
            )
            remaining = results._number_left
            pbar = tqdm(total=remaining)
            while True:
                pbar.update(remaining - results._number_left)
                if results.ready(): break
                remaining = results._number_left
                time.sleep(1)
            results = results.get()
            pool.close()
            pbar.close()
            g_list = [S2VGraph(g, g_label, n_labels, n_features,ind) for g, n_labels, n_features,ind in results]
           # max_n_label['value'] = max(
           #     max([max(n_labels) for _, n_labels, _ in results]), max_n_label['value']
           # )
            end = time.time()
            print("Time eplased for subgraph extraction: {}s".format(end-start))
            return g_list

    #print('Enclosing subgraph extraction begins...')
    train_graphs, test_graphs, val_graphs = None, None, None
    #if train_pos and train_neg:
    #print(type(train_pos))

#    g_B = nx.from_scipy_sparse_matrix(B)
#    g_B=g_B.to_directed()
    if train_pos is not None and train_neg is not None  :
        train_graphs = helper(A,B, train_pos, 1, DE_FLAG) + helper(A, B, train_neg, 0, DE_FLAG)
    #if test_pos and test_neg:
    if test_pos is not None and test_neg is not None:
        test_graphs = helper(A, B, test_pos, 1, DE_FLAG) + helper(A, B, test_neg, 0, DE_FLAG)

    if val_pos is not None and  val_neg is not None:
        val_graphs = helper(A, B, val_pos, 1, DE_FLAG) + helper(A, B, val_neg, 0, DE_FLAG)
    return train_graphs, test_graphs,val_graphs, 0#max_n_label['value']

def parallel_worker(x):
    return subgraph_extraction_labeling(*x)

def oldest_subgraph_extraction_labeling(ind, A, B, h=1, max_nodes_per_hop=None,
                                 node_information=None):
    # extract the h-hop enclosing subgraph around link 'ind'
    dist = 0
    nodes =[]#set()
    visited =[]# set()
    fringe = []#set()
    #nodes.add(ind)
    nodes[0]=ind
    visited[0]=ind
    fringe[0]=ind
    #fringe.add(ind)
    #nodes_dist = [0]# it was [0,0]
    for dist in range(1, h+1):
        fringe = neighbors(fringe, A)
        fringe = fringe - visited
        visited = union_list(visited,fringe)
        if max_nodes_per_hop is not None:
            if max_nodes_per_hop < len(fringe):
                fringe = random.sample(fringe, max_nodes_per_hop)
        if len(fringe) == 0:
            break
        nodes = nodes.union(fringe)
    nodes.remove(ind)
    nodes = [ind] + list(nodes)
    subgraph = A[nodes, :][:, nodes]
    if len(nodes)==1:
        labels=np.ones(1)
    else:
        #labels=np.zeros(1)
        labels=np.ones(1)
        x=len(nodes)-1
        while x > 0:

            labels=np.append(labels,[0],0)
    
            x=x-1
        #print(labels)
        #print(type(labels))
      #subgraph = A[nodes, :][:, nodes]
      # apply node-labeling
        labels=labels.astype(int)
        #labels = node_label(subgraph)

        #print(labels)
        #print(type(labels))
    # get node features
    features = None
    if node_information is not None:
        features = node_information[nodes]
    # construct nx graph
    g = nx.from_scipy_sparse_matrix(subgraph)
    # remove link between target nodes
    #if g.has_edge(0, 1):
     #   g.remove_edge(0, 1)
    return g, labels.tolist(), features

def subgraph_extraction_labeling(ind, A, B, h=1, max_nodes_per_hop=None,
                                 node_information=None,DE_FLAG=True):
    #print("Inside Subgraph Extraction Labeling")
    # extract the h-hop enclosing subgraph around link 'ind'
    dist = 0
    nodes =[]#set()
    visited = []#set()
    fringe = []#set()
    #distances={}
    #distances[ind]=1
    nodes.append(ind)#.add(ind)
    visited.append(ind)#.add(ind)
    fringe.append(ind)#.add(ind)
    #nodes_dist = [0]# it was [0,0]
    labels=np.zeros(1)
    for dist in range(1, h+1):
        if dist==1:

            fan_out, fan_in=direction(ind,A,B)
            visited = union_list(visited,fan_out)

            for e in fan_out:
                 #distances[e]=dist*(-1)
                labels=np.append(labels,[(dist*-1)],0)
                nodes = union_list(nodes,fan_out)
            visited = union_list(visited,fan_in)

            for e in fan_in:
                 #distances[e]=dist*(-1)
                labels=np.append(labels,[dist],0)
                nodes = union_list(nodes,fan_in)
        else:
            if len(fan_out)>0:
                fringe=fan_out
                fringe = neighbors(fringe, A)
                fringe = subtract_list(fringe,visited)
                visited = union_list(visited,fringe)

                for e in fringe:
                 #distances[e]=dist*(-1)
                    labels=np.append(labels,[(dist*-1)],0)
                nodes = union_list(nodes,fringe)
                #nodes_dist += [dist] * len(fringe)
                fan_out=fringe

            if len(fan_in)>0:
                fringe=fan_in
                fringe = neighbors(fringe, A)
                fringe = subtract_list(fringe,visited)
                #visited = visited.union(fringe)

                visited = union_list(visited,fringe)
                for e in fringe:
                 #distances[e]=dist*(-1)
                    labels=np.append(labels,[dist],0)

                nodes = union_list(nodes,fringe)
#nodes = nodes.union(fringe)
                #nodes_dist += [dist] * len(fringe)
                fan_in=fringe
#if max_nodes_per_hop is not None:
        #    if max_nodes_per_hop < len(fringe):
        #        fringe = random.sample(fringe, max_nodes_per_hop)
        #if len(fringe) == 0:
        #    break
    # move target node to top
    #nodes.remove(ind)
    #nodes = [ind] + list(nodes)
    subgraph = A[nodes, :][:, nodes]
    #print(nodes)





    #print(labels)
    #print(type(labels))

      # apply node-labeling
    labels=labels.astype(int)

    # get node features
    features = []
    if node_information is not None:
        i=0
        for node in nodes:
            vector=[]
            vector=list(node_information[node])
            one_hot=None
            if labels[i]==-2:
                one_hot=[1,0,0,0,0]

            elif labels[i]==1:
                one_hot=[0,0,0,1,0]

            elif labels[i]==2:
                one_hot=[0,0,0,0,1]
            elif labels[i]==-1:
                one_hot=[0,1,0,0,0]

            elif labels[i]==0:
                one_hot=[0,0,1,0,0]

            if DE_FLAG:
                #print("We are performing distance encoding")
                vector.extend(one_hot)#append(float(labels[i]))
            else:

                print("We are not performing distance encoding")
            #print("For node "+str(node)+" the feature is now ")
            #print(vector)
            features.append(vector)
            i=i+1
    features_=np.array(features)
    #print("Mine")
    #print(features_)
    #print(type(features_))

    #print(features_.dtype)
    features_ = np.float32(features_)
    # construct nx graph
    g = nx.from_scipy_sparse_matrix(subgraph)
    #print(type(g))
    #exit()
    g.nodes.data('foo', default=ind)    
#g.nodes[0]["key gate"]=indi
    #print(labels.shape)
    if len(nodes)==1:
        #print("Yes I have a single node\n")
        #print(labels.shape)

        labels=labels.reshape(1,1)

    #features = None
    #if node_information is not None:
    #    features = node_information[nodes]
    #print(type(features))

    #print("Before")
    #print(features)
    #print(features.dtype)
    return g, labels.tolist(), features_, ind
def old_subgraph_extraction_labeling(ind, A, B, h=1, max_nodes_per_hop=None,
                                 node_information=None):
    # extract the h-hop enclosing subgraph around link 'ind'
    dist = 0
    nodes =set()
    visited = set()
    fringe = set()
    #distances={}
    #distances[ind]=1
    nodes.add(ind)
    visited.add(ind)
    fringe.add(ind)
    #nodes_dist = [0]# it was [0,0]
    labels=np.ones(1)
    for dist in range(1, h+1):
        fringe = neighbors(fringe, A)
        fringe = fringe - visited
        visited = visited.union(fringe)
        if max_nodes_per_hop is not None:
            if max_nodes_per_hop < len(fringe):
                fringe = random.sample(fringe, max_nodes_per_hop)
        if len(fringe) == 0:
            break
        for e in fringe:
             #distances[e]=dist*(-1)
             labels=np.append(labels,[(dist*-1)],0)
        nodes = nodes.union(fringe)
        #nodes_dist += [dist] * len(fringe)
    # move target node to top
    nodes.remove(ind)
    nodes = [ind] + list(nodes)
    subgraph = A[nodes, :][:, nodes]
    #print(nodes)





    #print(labels)
    #print(type(labels))

      # apply node-labeling
    labels=labels.astype(int)

    # get node features
    features = None
    if node_information is not None:
        features = node_information[nodes]
    # construct nx graph
    g = nx.from_scipy_sparse_matrix(subgraph)

    return g, labels.tolist(), features
def direction(node,A,B):
    #print("Inside Direction for node "+str(node))
    #print("This is the successors:")
    #print(list(g.successors(node)))

    #print("This is the predecessors:")
    #print(set(list(g.predecessors(node))))
    fri=set()
    fri.add(node)
    res=neighbors(fri,A)
    #print("Those are neighbors!")
    #print(res)

    fan_in=neighbors_fanin(fri,B)

    #fan_out=res.copy()#set(list(g.successors(node)))
    #print("Those are fanin neighbors!")
    #print(fan_in)

    fan_out=neighbors_fanout(fri,B)
    #print("Those are fan out neighbors!")
    #print(fan_out)
    #fan_in=res.copy()#set(list(g.predecessors(node)))
    return fan_out, fan_in
def neighbors(fringe, A):
    # find all 1-hop neighbors of nodes in fringe from A
    res = []
    for node in fringe:
        nei, _, _ = ssp.find(A[:, node])
        nei = list(nei)
        res = union_list(res,nei)
    return res

def neighbors_fanin(fringe, A):
    # find all 1-hop neighbors of nodes in fringe from A
    res = []
    for node in fringe:
        nei, _, _ = ssp.find(A[:, node])
        nei = list(nei)
        res = union_list(res,nei)
    return res

def neighbors_fanout(fringe, A):
    # find all 1-hop neighbors of nodes in fringe from A
    res = []
    for node in fringe:
        _, nei, _ = ssp.find(A[node, :])
        nei = list(nei)
        res = union_list(res,nei)
    return res
def node_label(subgraph):
    # an implementation of the proposed double-radius node labeling (DRNL)
    K = subgraph.shape[0]
    subgraph_wo0 = subgraph[1:, 1:]
    subgraph_wo1 = subgraph[[0]+list(range(2, K)), :][:, [0]+list(range(2, K))]
    dist_to_0 = ssp.csgraph.shortest_path(subgraph_wo0, directed=False, unweighted=True)
    dist_to_0 = dist_to_0[1:, 0]
    dist_to_1 = ssp.csgraph.shortest_path(subgraph_wo1, directed=False, unweighted=True)
    dist_to_1 = dist_to_1[1:, 0]
    d = (dist_to_0 + dist_to_1).astype(int)
    d_over_2, d_mod_2 = np.divmod(d, 2)
    labels = 1 + np.minimum(dist_to_0, dist_to_1).astype(int) + d_over_2 * (d_over_2 + d_mod_2 - 1)
    #print(len(labels))
    #a=np.ones(len(labels))
    #a=a+1
    #labels=np.concatenate(np.array([1]),a)
    labels = np.concatenate((np.array([1, 1]), labels))
    labels[np.isinf(labels)] = 0
    labels[labels>1e6] = 0  # set inf labels to 0
    labels[labels<-1e6] = 0  # set -inf labels to 0
    return labels


def generate_node2vec_embeddings(A, emd_size=128, negative_injection=False, train_neg=None):
    if negative_injection:
        row, col = train_neg
        A = A.copy()
        A[row, col] = 1  # inject negative train
        A[col, row] = 1  # inject negative train
    nx_G = nx.from_scipy_sparse_matrix(A)
    G = node2vec.Graph(nx_G, is_directed=False, p=1, q=1)
    G.preprocess_transition_probs()
    walks = G.simulate_walks(num_walks=10, walk_length=80)
    walks = [list(map(str, walk)) for walk in walks]
    #print(walks)
    model = Word2Vec(walks, vector_size=emd_size, window=10, min_count=0, sg=1,
            workers=8, epochs=1)
    wv = model.wv
    embeddings = np.zeros([A.shape[0], emd_size], dtype='float32')
    sum_embeddings = 0
    empty_list = []
    for i in range(A.shape[0]):
        if str(i) in wv:
            embeddings[i] = wv.word_vec(str(i))
            sum_embeddings += embeddings[i]
        else:
            empty_list.append(i)
    mean_embedding = sum_embeddings / (A.shape[0] - len(empty_list))
    embeddings[empty_list] = mean_embedding
    return embeddings


def AA(A, test_pos, test_neg):
    # Adamic-Adar score
    A_ = A / np.log(A.sum(axis=1))
    A_[np.isnan(A_)] = 0
    A_[np.isinf(A_)] = 0
    sim = A.dot(A_)
    return CalcAUC(sim, test_pos, test_neg)
def union_list(first_list,second_list):
    resulting_list = list(first_list)
    resulting_list.extend(x for x in second_list if x not in resulting_list)
    return resulting_list

def subtract_list(first_list,second_list):
    resulting_list = []#list(first_list)
    resulting_list.extend(x for x in first_list if x not in second_list)
    return resulting_list
def CN(A, test_pos, test_neg):
    # Common Neighbor score
    sim = A.dot(A)
    return CalcAUC(sim, test_pos, test_neg)


def CalcAUC(sim, test_pos, test_neg):
    pos_scores = np.asarray(sim[test_pos[0], test_pos[1]]).squeeze()
    neg_scores = np.asarray(sim[test_neg[0], test_neg[1]]).squeeze()
    scores = np.concatenate([pos_scores, neg_scores])
    labels = np.hstack([np.ones(len(pos_scores)), np.zeros(len(neg_scores))])
    fpr, tpr, _ = metrics.roc_curve(labels, scores, pos_label=1)
    auc = metrics.auc(fpr, tpr)
    return auc

