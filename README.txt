Steps to follow:

1) Lock the netlist using lock_netlist.sh.

2) Go to circuit_datasets. Change the RLL_self_reference_track key to 64/128 based on keysize.

3) Run synRelockResyn.py. This will first synthesize RLL circuit with resyn2 (ALMOST recipe as well if resyn2 is changed with ALMOST recipe), relock the circuit 1000 times (900 training, 100 validation) and store the data in design_resynRelocked folder. The test circuit is the one which needs to be broken by the attacker. Also, for training the model, it will additionally create two other folders: resynRelockedResyn and resynRelockedRandomResyn. This indicates: i) The attacker has used only resyn2 to resynthesize all the relocked circuit to create training and validation data and ii) The attacker has randomly resynthesized the relocked netlist to create the training and validation data.

4) Change path of theCircuit.pm in netlist_to_subgraphs_cluster_version.pl

5) Run netlist_to_subgraph_data_gen.sh. This will create the sub-graph data generation compatible to train ML attack models.

6) There are four distinct folders inside OMLA repository: origRelockedCkt, trainTestCkt, graphDataCkt, and dumpDataCkt. origRelockedCkt contains all the relocked circuit from folder circuit_datasets/resynRelocked. trainTestCkt has all the circuits from circuit_datasets/resynRelockedRandomSyn. The content of these two folders are only going to be used when adversarial ML model is trained. For basic model training for e.g. resyn2, random or ALMOST synthesized relocked and resynthesized circuits; content from  graphDataCkt going to be used.

6) Running netlist_to_subgraph_data_gen.sh is going to create two folders: c1355_resyn and c1355_random in OMLA directory. Copy these two folders under graphDataCkt. Create two copies of c1355_random and rename one as c1355_sa. c1355_sa is the folder which will be regularly updated when adversarial model is trained. Basic attack models trained with static data from c1355_resyn and c1355_random take less time to train.

7) Run train_c1355.sh. Here, three models are trained. resyn2 is default OMLA attack model. random is ML model trained with arbitrary random synthesis recipe. sa is adversarially trained model. The models will be saved in dumpDataCkt.

8) Now, go to ALMOST/src and run c1355_generate_recipe.sh. This will use three pre-trained ML attacks models as evaluator in simulated annealing. After running SA for certain iterations (currently set at 110), this will generate the best recipe targeted to minimize accuracy to 50%.. The synthesized netlist will be in ALMOST/dump folder.
