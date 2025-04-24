import os
import sys

era = "Run3_2022EE"
ver = "2022EERun3_20250327"
indir = f"/eos/user/y/yumeng/HH_bbtautau_Run3/histograms/{ver}/{era}/merged/"
plotdir = f"/eos/user/y/yumeng/php-plots/hhbbtautau/{ver}/tautau_m_vis"

#varnames = ["tau1_pt", "tau2_pt", "b1_pt", "b2_pt", "tautau_m_vis", "bb_m_vis", "MT2"] #"PV_npvs", "bbtautau_mass"
varnames = ["tautau_m_vis"]
channellist = ["eE", "eMu", "muMu", "eTau", "muTau", "tauTau"]

categories = [
    "inclusive",
    "baseline",
    "btag_shape",
    
    "res0b_inclusive",
    "res1b_inclusive",
    "res2b_inclusive",
    "res0b_cat3",
    "res1b_cat3",
    "res2b_cat3",
    
    "boosted",
    "boosted_baseline",
    "boosted_baseline_cat3",
    "boosted_cat3",
    "boosted_cat3_masswindow"
]

using_uncertainties = True #When we turn on Up/Down, the file storage changes due to renameHists.py

for var in varnames:
    for channel in channellist:
        for cat in categories:
            filename = os.path.join(indir, var, f"{var}.root")
            print("Loading fname ", filename)

            outdir = os.path.join(plotdir, cat)
            os.makedirs(outdir, exist_ok=True)
            outname = os.path.join(outdir, f"HHbbtautau_{channel}_{var}_StackPlot.pdf")

            if using_uncertainties:
                filename = os.path.join(indir, var, 'tmp', f"all_histograms_{var}_hadded.root")

            want_data = False
            if channel in ["eE", "eMu", "muMu"]:
                want_data = True
            elif channel in ["eTau", "muTau", "tauTau"] and cat == "inclusive":
                want_data = True

            cmd = f"python3 ../FLAF/Analysis/HistPlotter.py --inFile {filename} --outFile {outname}"
            cmd += f" --bckgConfig ../config/background_samples.yaml --globalConfig ../config/global.yaml "
            cmd += f" --var {var} --category {cat} --channel {channel}"
            if want_data:
                cmd += " --wantData"
            cmd += f" --uncSource Central --year {era} --wantQCD False --rebin False --analysis HH_bbtautau --qcdregion OS_Iso"
            cmd += f" --sigConfig ../config/{era}/samples.yaml --wantSignals"

            os.system(cmd)
