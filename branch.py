import ROOT

f = ROOT.TFile.Open("/eos/user/y/yumeng/HH_bbtautau_Run3/anaTuples/2022EERun3_20250327/Run3_2022EE/DYto2L_M_10to50_amcatnloFXFX/nano_1.root")
f.ls()  # to find TTree name

tree = f.Get("Events")  # replace with actual TTree name
for branch in tree.GetListOfBranches():
    print(branch.GetName())

