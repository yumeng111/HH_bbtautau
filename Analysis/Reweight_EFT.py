import argparse
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
import numpy as np
import os
import re
import pickle
import warnings
warnings.filterwarnings("ignore", message=".*DataFrame is highly fragmented.*") ## just to avoid a lot of Performancewarnings 

parser = argparse.ArgumentParser(description = "EFT Reweighting for HH->bbtautau from parquet")
parser.add_argument('-e', '--era', type=str, dest='era', required=True, choices=['Run3_2022postEE', 'Run3_2022preEE', 'Run3_2022', 'Run3_2023preBPix', 'Run3_2023postBPix', 'Run3_2023'], help='Era to chose, choices available: Run3_2022postEE, Run3_2022preEE, Run3_2022, Run3_2023preBPix, Run3_2023postBPix, Run3_2023')
parser.add_argument('-o', '--output', type=str, dest='output', default="./Reweighted_parquets/", help='output folder to save reweighted parquet files and control plots')
parser.add_argument('--HEFT_only', action='store_true', dest='HEFT_only', default=False, help='If true, process only HEFT. If false, process HEFT and SMEFT weights. Default is False')
parser.add_argument('--map_eras_file', type=str, dest='map_eras_file', default="./docs/v2/map_eras.yaml", help='Path to the map eras file. Default is ./docs/v2/map_eras.yaml')
parser.add_argument('--nominal-only', action='store_true', dest='nominal_only', default=True, help='If true, process only nominal components')
parser.add_argument('--SM-only', action='store_true', dest='SM_only', default=False, help='If true, process only SM sample. If false, process all samples. Default is False.')
parser.add_argument('--No-SM', action='store_true', dest='No_SM', default=False, help='If true, do not include SM sample in input samples. Default is False.')
parser.add_argument('-d','--dim', type=int, dest='dim', default=1, help='Dimension of the HEFT reweighting. 1 or 2. Default is 1. Only 3D for SMEFT.')
parser.add_argument('--coeffs-from_arxiv-2304-01968', action='store_true', dest='coeffs_from_arxiv', default=False, help='If true and 1D, use the 1D coefficients from arxiv-2304-01968 for HEFT. Default is False. If False, use the coefficients from Matheus Study. SMEFT only from arxiv 2502.20976')
parser.add_argument('--use-variables-file', action='store_true', dest='use_variables_file', default=False, help='If true, use the variables file to select the variables to read. If false, read all variables in the parquet files. Default is False.')
parser.add_argument('--input-parquet-dir', type=str, dest='input_parquet_dir', default=None, help='Directory containing input parquet files. If not specified, will use map_eras_file.')

args = parser.parse_args()

## Get the options
nominal_only = args.nominal_only
SM_only = args.SM_only
HEFT_only = args.HEFT_only
outputDir = args.output + "/"
if args.era == "Run3_2022":
    run_eras = ["Run3_2022", "Run3_2022EE"]
elif args.era == "Run3_2023":
    run_eras = ["Run3_2023", "Run3_2023BPix"]
else:
    run_eras = [args.era]

dim = args.dim
if dim not in [1,2]:
    raise ValueError("Dimension must be 1 or 2. You provided: {}".format(dim))
coeffs_from_arxiv = args.coeffs_from_arxiv
map_eras_file = args.map_eras_file
use_variables_file = args.use_variables_file
No_SM = args.No_SM

if SM_only and No_SM:
    raise ValueError("Impossible to have at the same time SM_only and No_SM.")

# Helper functions
def read_yaml(yaml_file):
    """Read YAML file and return dictionary"""
    import yaml
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)

def read_parket_pd(path, sample, cat, era, columns=None, type_correction="nominal"):
    """Read parquet file and return pandas dataframe
    
    Args:
        path: path to parquet file or directory
        sample: sample name
        cat: category (not used in bbtautau, kept for compatibility)
        era: era string
        columns: list of columns to read (if None, read all)
        type_correction: systematic variation type
    """
    if os.path.isfile(path):
        parquet_path = path
    else:
        # Construct path based on correction type
        if type_correction == "nominal" or type_correction == "":
            parquet_path = os.path.join(path, f"{sample}.parquet")
        else:
            parquet_path = os.path.join(path, type_correction, f"{sample}.parquet")
    
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
    
    print(f"Reading parquet file: {parquet_path}")
    
    if columns and len(columns) > 0:
        df = pd.read_parquet(parquet_path, columns=list(columns.keys()))
    else:
        df = pd.read_parquet(parquet_path)
    
    return df

def exist_or_make(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)

# Get the map era and variables dictionaries
if args.input_parquet_dir is None and map_eras_file is not None:
    map_eras = read_yaml(map_eras_file)
else:
    map_eras = None

if use_variables_file:
    variables_file = "configs/variables.yaml"  
    all_variables = read_yaml(variables_file)
else:
    all_variables = {} # Here, we do not use the variables file, we directly take all variables in the file

# Get the input samples to reweight
# For bbtautau, the signal sample names should be like: GluGluToHHTo2B2Tau_kl_X_kt_Y_c2_Z
pattern_signals_keys = r"^GluGlutoHHto2B2Tau_kl_([0-9]+[pm][0-9]+)_kt_([0-9]+[pm][0-9]+)_c2_([0-9]+[pm][0-9]+)$"

if map_eras is not None:
    list_samples_file = map_eras[run_eras[0]]['list_samples']
    dict_samples = read_yaml(list_samples_file)
    signals = [key for key, value in dict_samples.items() if re.match(pattern_signals_keys,key)] #Will define the input parquet files (without SM one)
else:
    # If no map_eras file, look for parquet files directly
    signals = []
    if args.input_parquet_dir is not None:
        for file in os.listdir(args.input_parquet_dir):
            if file.endswith('.parquet') and re.match(pattern_signals_keys, file.replace('.parquet', '')):
                signals.append(file.replace('.parquet', ''))

print("Signals : ")
print(signals)

if not No_SM:
    signals.append("GluGluToHH")

signal_SM = ["GluGluToHH"] # Define the input parquet files for the SM signal
signals_tot = list(np.unique(signals + signal_SM)) if not SM_only else signal_SM # If SM_only is True, only keep the SM signal

corrections_types = ["nominal","Et_dependent_ScaleEB_down","Et_dependent_ScaleEB_up","Et_dependent_ScaleEE_down","Et_dependent_ScaleEE_up","Et_dependent_Smearing_down","Et_dependent_Smearing_up","jec_syst_Total_down","jec_syst_Total_up","jer_syst_down","jer_syst_up"]
if nominal_only:
    corrections_types = ["nominal"] # For most samples, this is given without other samples than nominal and thus there is no subfolders

## Get the EFT points list
HEFT_points_file = "configs/HEFT_points_out.yaml"
HEFT_points = read_yaml(HEFT_points_file)
HEFT_points_list = {key for key, value in HEFT_points.items()}

if not HEFT_only:
    SMEFT_points_file = "configs/SMEFT_points_out.yaml"
    SMEFT_points = read_yaml(SMEFT_points_file)
    SMEFT_points_list = {key for key, value in SMEFT_points.items()}

## Run the reweighting on all correction types needed
for correction_type in corrections_types:
    df_signals = pd.DataFrame() # Initialize Dataframe containing the sample to weight
    df_SM = pd.DataFrame() # Initialize Dataframe containing the SM sample
    
    ## Get the dataframe corresponding to input parquet files
    for run_era in run_eras:
        if map_eras is not None:
            list_samples_folders = map_eras[run_era]['list_samples']
            samples = read_yaml(list_samples_folders)
        else:
            samples = {s: {'path': args.input_parquet_dir} for s in signals_tot}
        
        for signal in signals_tot:
            print(run_era+" "+signal+" "+correction_type)
            path_cat = samples[signal]['path']
            df_local = read_parket_pd(path_cat,signal,0,run_era,columns = all_variables,type_correction=correction_type) # use type_correction="" and add correction type directly to path_cat. Otherwise, will load all correction types
            
            if signal in signals:
                try:
                    df_signals = df_local if len(df_signals) == 0 else df_signals._append(df_local)
                except:
                    df_signals = df_local if len(df_signals) == 0 else df_signals.append(df_local)
            
            if signal in signal_SM:
                try:
                    df_SM = df_local if len(df_SM) == 0 else df_SM._append(df_local)
                except:
                    df_SM = df_local if len(df_SM) == 0 else df_SM.append(df_local)
    
    # Check if gen-level variables exist
    required_gen_vars = ['gen_mHH', 'gen_CosThetaStar_HH', 'gen_pT_HH']
    missing_vars = [var for var in required_gen_vars if var not in df_SM.columns]
    if missing_vars:
        raise ValueError(f"ERROR: The following required gen-level variables are missing from the input parquet files: {missing_vars}\n"
                        f"Please ensure your parquet files contain: gen_mHH, gen_CosThetaStar_HH, gen_pT_HH\n"
                        f"These should be added during the tuple production step.")
    
    # Set the bin edges for HEFT and SMEFT
    bin_edges_cosThetaStar_HEFT = np.array([0.0,0.4,0.6,0.8,1.0])
    if dim == 1 and coeffs_from_arxiv: # The binning scheme for 1D coefficients from arxiv-2304-01968 for HEFT
        bin_edges_mhh_HEFT = np.array([250,270,290,310,330,350,370,390,410,430,450,470,490,510,530,
                            550,570,590,610,630,650,670,690,710,730,750,770,790,810,830,
                            850,870,890,910,930,950,970,990,1010,1030,1050,1200,1400,3000])   # binning stop at 1400 and we apply the same A for mhh>1400
    else: # Binning scheme in other HEFT cases
        bin_edges_mhh_HEFT = np.array([250,270,290,310,330,350,370,390,410,430,450,470,490,510,
                            530,550,570,590,610,630,650,670,690,710,730, 750, 800, 850, 900,
                            950, 1000, 1050, 1150, 1200, 1300, 1400, 1500, 1600, 1800, 2000, 3000])
    
    bin_edges_mhh_SMEFT = np.array([250,270,290,310,330,350,370,390,410,430,450,490,530,570,
                                  610,650,700,750,800,850,900,1000,1200,1400,3000]) # binning stop at 1400 and we apply the same A for mhh>1400
    bin_edges_cosThetaStar_SMEFT = np.array([0.0,0.25,0.5,0.75,1.0])
    bin_edges_pthh_SMEFT = np.array([0.,20.,40.,70.,100.,140.,200.,290.,2500.])
    
    nBins_mhh_HEFT = len(bin_edges_mhh_HEFT)-1
    nBins_cosThetaStar_HEFT = len(bin_edges_cosThetaStar_HEFT)-1
    nBins_mhh_SMEFT = len(bin_edges_mhh_SMEFT)-1
    nBins_cosThetaStar_SMEFT = len(bin_edges_cosThetaStar_SMEFT)-1
    nBins_pthh_SMEFT = len(bin_edges_pthh_SMEFT)-1
    
    # Get the SM signal fractions
    if dim == 1:
        h_SM_HEFT, _ = np.histogram(df_SM["gen_mHH"], bins=bin_edges_mhh_HEFT)
    if dim == 2:
        h_SM_HEFT, _, _ = np.histogram2d(np.abs(df_SM["gen_CosThetaStar_HH"]), df_SM["gen_mHH"], bins=[bin_edges_cosThetaStar_HEFT, bin_edges_mhh_HEFT])
    
    h_SM_HEFT_unc = np.sqrt(h_SM_HEFT)
    fractions_SM_HEFT = h_SM_HEFT / np.sum(h_SM_HEFT) #Frac_i^SM
    unc_fractions_SM_HEFT = np.sqrt(h_SM_HEFT) / np.sum(h_SM_HEFT)
    
    h_SM_SMEFT, _ = np.histogramdd(
        sample=np.column_stack((
            np.abs(df_SM["gen_CosThetaStar_HH"]),
            df_SM["gen_pT_HH"],
            df_SM["gen_mHH"]
            )),
        bins=[bin_edges_cosThetaStar_SMEFT, bin_edges_pthh_SMEFT, bin_edges_mhh_SMEFT]
        )
    h_SM_SMEFT_unc = np.sqrt(h_SM_SMEFT)
    fractions_SM_SMEFT = h_SM_SMEFT / np.sum(h_SM_SMEFT) #Frac_i^SM
    unc_fractions_SM_SMEFT = np.sqrt(h_SM_SMEFT) / np.sum(h_SM_SMEFT)
    
    ## Get the signal histogram for later normalisation
    if dim == 1:
        h_signal_HEFT, _ = np.histogram(df_signals["gen_mHH"], bins=bin_edges_mhh_HEFT)
    if dim == 2:
        h_signal_HEFT, _, _ = np.histogram2d(np.abs(df_signals["gen_CosThetaStar_HH"]), df_signals["gen_mHH"], bins=[bin_edges_cosThetaStar_HEFT, bin_edges_mhh_HEFT])
    h_signal_unc_HEFT = np.sqrt(h_signal_HEFT)
    
    h_signal_SMEFT, _ = np.histogramdd(
        sample=np.column_stack((
            np.abs(df_signals["gen_CosThetaStar_HH"]),
            df_signals["gen_pT_HH"],
            df_signals["gen_mHH"]
            )),
        bins=[bin_edges_cosThetaStar_SMEFT, bin_edges_pthh_SMEFT, bin_edges_mhh_SMEFT]
        )
    h_signal_SMEFT_unc = np.sqrt(h_signal_SMEFT)
    
    print("number events in input samples : {}".format(np.sum(h_signal_HEFT)))
    
    ## Get the parameterisation coefficients for HEFT
    binning_version = ""
    if dim == 1 and coeffs_from_arxiv:
        # Get the coefficients from the arxiv-2304-01968 paper
        binning_version = "1D_mhh_arxiv_2304_01968"
        with open("Coefficients_EFT/1D_mhh_arxiv_2304_01968/HEFT_dA_and_A_with_Binning_250_1050_41_Variable_Bins_1200_1400_muR_muF_1.txt", "r") as f:
            lines = f.readlines()[:-1]  # remove the last line which are the inclusive a coefficients
        coeffs_HEFT = np.array([list(map(float, line.strip().split())) for line in lines])
        coeffs_HEFT = coeffs_HEFT[:, 1:] # Remove the first element of each line which is the central mhh of the bin
        coeffs_HEFT = np.append(coeffs_HEFT,[coeffs_HEFT[-1]],axis=0) # Add the last line again to apply the last bin coefficient to m_hh > 1400
        
        ## Get the coefficients uncertainties
        with open("Coefficients_EFT/1D_mhh_arxiv_2304_01968/HEFT_CovMat_for_dA_muR_muF_1.txt", 'r') as f:
            lines = f.readlines()
        
        n_coeffs_HEFT = 23
        CovMatrices = []
        i = 0
        while i < len(lines):
            block = []
            
            # first ligne of each block : central mhh of the bin + first line of the cov matrix
            parts = lines[i].strip().split()
            row = [float(x) for x in parts[1:]]
            block.append(row)
            i += 1
            # 22 other lines : lines of the cov matrix
            for _ in range(n_coeffs_HEFT - 1):
                parts = lines[i].strip().split()
                row = [float(x) for x in parts]
                block.append(row)
                i += 1
            # load the matrix
            CovMatrices.append(np.array(block))
        
        # Calculate the errors (square root of diagonal elements of the cov matrix)
        coeffs_unc_HEFT = [np.sqrt(np.diag(mat)) for mat in CovMatrices]
        coeffs_unc_HEFT = np.append(coeffs_unc_HEFT,[coeffs_unc_HEFT[-1]],axis=0) # Add the last line again to apply the last bin coefficient to m_hh > 1400
    
    elif dim == 1:
        binning_version = "1D_mhh"
        data = np.loadtxt(f"Coefficients_EFT/1D_mhh/1000samples_heft_theta_0.0-1.0.txt", skiprows=2)
        coeffs_HEFT = np.array(data[:, :23].tolist())
        coeffs_unc_HEFT = np.array(data[:, 23:].tolist())
    
    elif dim == 2:
        binning_version = "2D_cosThetaStar_mhh"
        coeffs_HEFT = []
        coeffs_unc_HEFT = []
        for i in range(nBins_cosThetaStar_HEFT):
            data = np.loadtxt(f"Coefficients_EFT/2D_cosThetaStar_mhh/1000samples_heft_theta_{bin_edges_cosThetaStar_HEFT[i]:.1f}-{bin_edges_cosThetaStar_HEFT[i+1]:.1f}.txt", skiprows=2)
            coeffs_HEFT.append(data[:, :23].tolist())
            coeffs_unc_HEFT.append(data[:, 23:].tolist())
        
        # Convert to numpy arrays
        coeffs_HEFT = np.array(coeffs_HEFT)
        coeffs_unc_HEFT = np.array(coeffs_unc_HEFT)
    
    ## Get the parametrisation coefficients for SMEFT
    if not HEFT_only:
        # Reading the .pkl file containing SMEFT coefficients
        SMEFT_coeffs_file = "./Coefficients_EFT/3D_SMEFT/SMEFT_formula_with_error.pkl"
        print("Reading file " + SMEFT_coeffs_file)
        with open(SMEFT_coeffs_file, "rb") as f:
            readout_coeffs_SMEFT = pickle.load(f)
        
        Input_coeffs_SMEFT = list(readout_coeffs_SMEFT["res"]) # not direct as the order of values is not convenient with the following
        Input_coeffs_unc_SMEFT = list(readout_coeffs_SMEFT["cov"]) # not direct as the order of values is not convenient with the following
        
        if len(Input_coeffs_SMEFT[0]) != nBins_cosThetaStar_SMEFT*nBins_pthh_SMEFT*(nBins_mhh_SMEFT-1):
            raise Exception("ERROR : the coefficients file for SMEFT does not correspond to the binning Scheme")
        
        coeffs_SMEFT = []
        coeffs_unc_SMEFT = []
        ix = 0
        for itheta in range(nBins_cosThetaStar_SMEFT):
            coeffs_SMEFT.append([])
            coeffs_unc_SMEFT.append([])
            for ip in range(nBins_pthh_SMEFT):
                coeffs_SMEFT[itheta].append([])
                coeffs_unc_SMEFT[itheta].append([])
                for im in range(nBins_mhh_SMEFT-1): # -1 because we added one bin for high mhh events between 1400 and 3000
                    coeffs_SMEFT[itheta][ip].append([])
                    coeffs_unc_SMEFT[itheta][ip].append([])
                    for icoeff in range(len(Input_coeffs_SMEFT)):
                        coeffs_SMEFT[itheta][ip][im].append(Input_coeffs_SMEFT[icoeff][ix])
                        coeffs_unc_SMEFT[itheta][ip][im].append(Input_coeffs_unc_SMEFT[icoeff][icoeff][ix])
                    ix += 1
                coeffs_SMEFT[itheta][ip].append(coeffs_SMEFT[itheta][ip][im]) # we had an additional bin for 1400 < mhh < 3000 with last bin coefficient
                coeffs_unc_SMEFT[itheta][ip].append(coeffs_unc_SMEFT[itheta][ip][im])
    
    ## Get the normalisation (total number of events in each bins in samples without selection)
    N_events_raw_samples_HEFT = np.zeros_like(h_signal_HEFT, dtype=float)
    N_events_raw_SM_HEFT = np.zeros_like(h_signal_HEFT, dtype=float)
    N_events_raw_samples_SMEFT = np.zeros_like(h_signal_SMEFT, dtype=float)
    N_events_raw_SM_SMEFT = np.zeros_like(h_signal_SMEFT, dtype=float)
    
    for run_era in run_eras:
        if not SM_only:
            for signal in signals:
                N_events_raw_samples_HEFT += np.loadtxt(f"Normalisation_EFT_reweight/{binning_version}/{run_era}/Normalisation_EFT_{signal}.txt",skiprows=1)
                # For SMEFT
                if not HEFT_only:
                    with open(f"Normalisation_EFT_reweight/3D_SMEFT/{run_era}/Normalisation_EFT_{signal}.txt", "r") as file:
                        lines = file.readlines()
                    data_lines = [line for line in lines if not line.strip().startswith("#") and line.strip()] # Cut the comment lines
                    data = np.array([list(map(float, line.strip().split())) for line in data_lines]) # To float
                    N_events_raw_samples_SMEFT += data.reshape((nBins_cosThetaStar_SMEFT, nBins_pthh_SMEFT, nBins_mhh_SMEFT)) # reshape to binning shape
        else:
            for signal in signal_SM:
                N_events_raw_samples_HEFT += np.loadtxt(f"Normalisation_EFT_reweight/{binning_version}/{run_era}/Normalisation_EFT_{signal}.txt",skiprows=1)
                # For SMEFT
                if not HEFT_only:
                    with open(f"Normalisation_EFT_reweight/3D_SMEFT/{run_era}/Normalisation_EFT_{signal}.txt", "r") as file:
                        lines = file.readlines()
                    data_lines = [line for line in lines if not line.strip().startswith("#") and line.strip()] # Cut the comment lines
                    data = np.array([list(map(float, line.strip().split())) for line in data_lines]) # To float
                    N_events_raw_samples_SMEFT += data.reshape((nBins_cosThetaStar_SMEFT, nBins_pthh_SMEFT, nBins_mhh_SMEFT)) # reshape to binning shape
        
        for signal in signal_SM:
            N_events_raw_SM_HEFT += np.loadtxt(f"Normalisation_EFT_reweight/{binning_version}/{run_era}/Normalisation_EFT_{signal}.txt",skiprows=1)
            # For SMEFT
            if not HEFT_only:
                with open(f"Normalisation_EFT_reweight/3D_SMEFT/{run_era}/Normalisation_EFT_{signal}.txt", "r") as file:
                    lines = file.readlines()
                data_lines = [line for line in lines if not line.strip().startswith("#") and line.strip()] # Cut the comment lines
                data = np.array([list(map(float, line.strip().split())) for line in data_lines]) # To float
                N_events_raw_SM_SMEFT += data.reshape((nBins_cosThetaStar_SMEFT, nBins_pthh_SMEFT, nBins_mhh_SMEFT)) # reshape to binning shape
    
    N_events_raw_samples_unc_HEFT = np.sqrt(N_events_raw_samples_HEFT) # Uncertainty on the number of events in each bin
    N_events_raw_SM_unc_HEFT = np.sqrt(N_events_raw_SM_HEFT) # Uncertainty on the number of SM events in each bin
    N_events_raw_samples_unc_SMEFT = np.sqrt(N_events_raw_samples_SMEFT) # Uncertainty on the number of events in each bin
    N_events_raw_SM_unc_SMEFT = np.sqrt(N_events_raw_SM_SMEFT) # Uncertainty on the number of SM events in each bin
    
    Frac_events_raw_SM_HEFT = N_events_raw_SM_HEFT / np.sum(N_events_raw_SM_HEFT) # Fraction of events in each bin for the SM sample
    Frac_events_raw_SM_unc_HEFT = np.sqrt(N_events_raw_SM_HEFT) / np.sum(N_events_raw_SM_HEFT) # Uncertainty on the fraction of events in each bin for the SM sample
    Frac_events_raw_SM_SMEFT = N_events_raw_SM_SMEFT / np.sum(N_events_raw_SM_SMEFT) # Fraction of events in each bin for the SM sample
    Frac_events_raw_SM_unc_SMEFT = np.sqrt(N_events_raw_SM_SMEFT) / np.sum(N_events_raw_SM_SMEFT) # Uncertainty on the fraction of events in each bin for the SM sample
    
    ## Loop over all the HEFT points to reach and add corresponding weights
    xsec_SM = HEFT_points["ggHH_kl_1p00_kt_1p00_c2_0p00_cg_0p00_c2g_0p00"].get('xs') # Cross section target for the EFT point
    for EFT_point in HEFT_points_list:
        # Get the EFT point (if the parameter is not defined, put SM value as default)
        kl, kt, c2, cg, c2g = HEFT_points[EFT_point].get('kl', 1.), HEFT_points[EFT_point].get('kt', 1.), HEFT_points[EFT_point].get('c2', 0.), HEFT_points[EFT_point].get('cg', 0.), HEFT_points[EFT_point].get('c2g', 0.)
        
        xsec_target = HEFT_points[EFT_point].get('xs') # Cross section target for the EFT point
        print("Process point kl={:.2f}, kt={:.2f}, c2={:.2f}, cg={:.2f}, c2g={:.2f}".format(kl, kt, c2, cg, c2g))
        
        ## Get the parametrisation vector
        v_parameters = np.array([kt**4,                     #1
                                c2**2,                     #2
                                (kt**2)*(kl**2),       #3
                                (cg**2)*(kl**2),     #4
                                c2g**2,                   #5
                                c2*(kt**2),                #6
                                (kt**3)*kl,            #7
                                kt*kl*c2,             #8
                                cg*kl*c2,           #9
                                c2*c2g,                  #10
                                cg*kl*(kt**2),       #11
                                c2g*(kt**2),              #12
                                (kl**2)*cg*kt,       #13
                                c2g*kt*kl,           #14
                                cg*c2g*kl,         #15
                                (kt**3)*cg,               #16
                                kt*c2*cg,                #17
                                kt*(cg**2)*kl,       #18
                                kt*cg*c2g,              #19
                                (kt**2)*(cg**2),          #20
                                c2*(cg**2),              #21
                                (cg**3)*kl,          #22
                                (cg**2)*c2g])           #23
        
        v_parameters_SM = np.array([1.,0.,1.,0.,0.,0.,1.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.])
        
        # Get the polynomials and polynomial ratio between signal and SM
        # This is in fact not the polynomial here but the ratio between polynomials (see Chapter 4 of https://arxiv.org/pdf/2304.01968)
        poly_signal = np.dot(coeffs_HEFT,v_parameters)
        poly_signal_unc = np.sqrt(np.sum((coeffs_unc_HEFT*v_parameters)**2, axis=dim))
        poly_SM = np.dot(coeffs_HEFT,v_parameters_SM)
        poly_SM_unc = np.sqrt(np.sum((coeffs_unc_HEFT*v_parameters_SM)**2, axis=dim))
        poly = poly_signal / poly_SM # This is in fact not the polynomial here but the ratio between polynomials (see Chapter 4 of https://arxiv.org/pdf/2304.01968)
        poly_unc = np.sqrt((poly_signal_unc/poly_SM)**2 + (poly_SM_unc*poly_signal/poly_SM**2)**2) # This is the uncertainty on the ratio of polynomials
        
        ## Calculate the weight per bin
        ## Get the normalisation factor
        C_norm = 0
        C_norm_unc = 0 
        if dim == 1:
            for j in range(nBins_mhh_HEFT):
                C_norm += poly[j] * Frac_events_raw_SM_HEFT[j] * (xsec_SM/xsec_target)
                if Frac_events_raw_SM_HEFT[j] != 0:
                    C_norm_unc =  np.sqrt(C_norm_unc**2 + (poly[j] * Frac_events_raw_SM_HEFT[j] * (xsec_SM/xsec_target))**2 * ((poly_unc[j] / poly[j])**2 + (Frac_events_raw_SM_unc_HEFT[j] / Frac_events_raw_SM_HEFT[j])**2))   
        if dim == 2:
            for j in range(nBins_cosThetaStar_HEFT):
                for k in range(nBins_mhh_HEFT):
                    C_norm += poly[j][k] * Frac_events_raw_SM_HEFT[j][k] * (xsec_SM/xsec_target)
                    if N_events_raw_SM_HEFT[j][k] != 0:
                        C_norm_unc = np.sqrt(C_norm_unc**2 + (poly[j][k] * Frac_events_raw_SM_HEFT[j][k] * (xsec_SM/xsec_target))**2 * ((poly_unc[j][k] / poly[j][k])**2 + (Frac_events_raw_SM_unc_HEFT[j][k] / Frac_events_raw_SM_HEFT[j][k])**2))
        
        # Set the weight per bin
        weight_per_bin = np.zeros_like(poly, dtype=float) # initialise the weight to 0, notably for the case where the denominator is 0
        weight_per_bin_unc = np.zeros_like(poly, dtype=float) # initialise the weight to 0, notably for the case where the denominator is 0
        Mask_N_events_raw_samples = N_events_raw_samples_HEFT != 0
        Mask_N_events_raw_SM = N_events_raw_SM_HEFT != 0
        
        weight_per_bin[Mask_N_events_raw_samples] = (poly[Mask_N_events_raw_samples] / N_events_raw_samples_HEFT[Mask_N_events_raw_samples]) * (xsec_SM/xsec_target) * N_events_raw_SM_HEFT[Mask_N_events_raw_samples] / C_norm
        weight_per_bin_unc[Mask_N_events_raw_samples & Mask_N_events_raw_SM] =  weight_per_bin[Mask_N_events_raw_samples & Mask_N_events_raw_SM] * np.sqrt((poly_unc[Mask_N_events_raw_samples & Mask_N_events_raw_SM] / poly[Mask_N_events_raw_samples & Mask_N_events_raw_SM])**2 + (N_events_raw_samples_unc_HEFT[Mask_N_events_raw_samples & Mask_N_events_raw_SM] / N_events_raw_samples_HEFT[Mask_N_events_raw_samples & Mask_N_events_raw_SM])**2 + (N_events_raw_SM_unc_HEFT[Mask_N_events_raw_samples & Mask_N_events_raw_SM] / N_events_raw_SM_HEFT[Mask_N_events_raw_samples & Mask_N_events_raw_SM])**2 + (C_norm_unc / C_norm)**2)
        
        ## Apply the weight event by event
        # Get the bin of the event
        if dim == 1:
            # Find bin indice for each event
            bin_indices = np.digitize(df_signals['gen_mHH'], bin_edges_mhh_HEFT) - 1  # digitize begins at 1
            
            # Apply the weights if bin indice is valid # Set weight to 0 if out of binning scheme
            weights_EFT = np.zeros(len(df_signals), dtype=float)
            weights_EFT_unc = np.zeros(len(df_signals), dtype=float)
            valid = (bin_indices >= 0) & (bin_indices < nBins_mhh_HEFT)
            weights_EFT[valid] = weight_per_bin[bin_indices[valid]]
            weights_EFT_unc[valid] = weight_per_bin_unc[bin_indices[valid]]
        
        if dim == 2:
            # Find bin indice for each event
            bin_indices_mhh = np.digitize(df_signals['gen_mHH'], bin_edges_mhh_HEFT) - 1  # digitize begins at 1
            bin_indices_cosThetaStar = np.digitize(np.abs(df_signals['gen_CosThetaStar_HH']), bin_edges_cosThetaStar_HEFT) - 1  # digitize begins at 1
            
            # Apply the weights if bin indice is valid # Set weight to 0 if out of binning scheme
            weights_EFT = np.zeros(len(df_signals), dtype=float)
            weights_EFT_unc = np.zeros(len(df_signals), dtype=float)
            valid = (bin_indices_mhh >= 0) & (bin_indices_mhh < nBins_mhh_HEFT) & (bin_indices_cosThetaStar >= 0) & (bin_indices_cosThetaStar < nBins_cosThetaStar_HEFT)
            weights_EFT[valid] = weight_per_bin[bin_indices_cosThetaStar[valid], bin_indices_mhh[valid]]
            weights_EFT_unc[valid] = weight_per_bin_unc[bin_indices_cosThetaStar[valid], bin_indices_mhh[valid]]
        
        # Add the weight column
        df_signals["weight_EFT_kl_{:.2f}_kt_{:.2f}_c2_{:.2f}_cg_{:.2f}_c2g_{:.2f}".format(kl, kt, c2, cg, c2g).replace(".","p").replace("-","m")] = weights_EFT
        df_signals["weight_EFT_unc_kl_{:.2f}_kt_{:.2f}_c2_{:.2f}_cg_{:.2f}_c2g_{:.2f}".format(kl, kt, c2, cg, c2g).replace(".","p").replace("-","m")] = weights_EFT_unc
    
    ## Loop over all the SMEFT points to reach and add corresponding weights
    if not HEFT_only:
        xsec_SM = SMEFT_points["ggHH_CH_0p00_CHBox_0p00_CHD_0p00_CuH_0p00_CHG_0p00"].get('xs') # Cross section target for the SMEFT point
        for EFT_point in SMEFT_points_list:
            # Get the EFT point (if the parameter is not defined, put SM value as default)
            CH, CHBox, CHD, CuH, CHG = SMEFT_points[EFT_point].get('CH', 0.), SMEFT_points[EFT_point].get('CHBox', 0.), SMEFT_points[EFT_point].get('CHD', 0.), SMEFT_points[EFT_point].get('CuH', 0.), SMEFT_points[EFT_point].get('CHG', 0.)
            CH_kin = CHBox-0.25*CHD
            
            xsec_target = SMEFT_points[EFT_point].get('xs') # Cross section target for the EFT point
            print("Process point CH={:.2f}, CHBox={:.2f}, CHD={:.2f}, CuH={:.2f}, CHG={:.2f}".format(CH, CHBox, CHD, CuH, CHG))
            
            ## Get the parametrisation vector
            v_parameters = np.array([1,                     #1
                                    CH,                     #2
                                    CH_kin,       #3
                                    CuH,     #4
                                    CHG,                   #5
                                    CH**2,                #6
                                    CH_kin**2,            #7
                                    CuH**2,             #8
                                    CHG**2,           #9
                                    CH*CH_kin,                  #10
                                    CH*CuH,       #11
                                    CH*CHG,              #12
                                    CH_kin*CuH,       #13
                                    CH_kin*CHG,           #14
                                    CuH*CHG])         #15
            
            v_parameters_SM = np.array([1.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.])
            
            # Get the polynomials and polynomial ratio between signal and SM
            # This is in fact not the polynomial here but the ratio between polynomials (see Chapter 4 of https://arxiv.org/pdf/2304.01968)
            poly_signal = np.dot(coeffs_SMEFT,v_parameters)
            poly_signal_unc = np.sqrt(np.sum((coeffs_unc_SMEFT*v_parameters)**2, axis=3))
            poly_SM = np.dot(coeffs_SMEFT,v_parameters_SM)
            poly_SM_unc = np.sqrt(np.sum((coeffs_unc_SMEFT*v_parameters_SM)**2, axis=3))
            poly = poly_signal / poly_SM # This is in fact not the polynomial here but the ratio between polynomials (see Chapter 4 of https://arxiv.org/pdf/2304.01968)
            poly_unc = np.sqrt((poly_signal_unc/poly_SM)**2 + (poly_SM_unc*poly_signal/poly_SM**2)**2) # This is the uncertainty on the ratio of polynomials
            
            ## Calculate the weight per bin
            ## Get the normalisation factor
            C_norm = 0
            C_norm_unc = 0 
            for itheta in range(nBins_cosThetaStar_SMEFT):
                for ip in range(nBins_pthh_SMEFT):
                    for im in range(nBins_mhh_SMEFT):
                        C_norm += poly[itheta][ip][im] * Frac_events_raw_SM_SMEFT[itheta][ip][im] * (xsec_SM/xsec_target)
                        if N_events_raw_SM_SMEFT[itheta][ip][im] != 0:
                            C_norm_unc = np.sqrt(C_norm_unc**2 + (poly[itheta][ip][im] * Frac_events_raw_SM_SMEFT[itheta][ip][im] * (xsec_SM/xsec_target))**2 * ((poly_unc[itheta][ip][im] / poly[itheta][ip][im])**2 + (Frac_events_raw_SM_unc_SMEFT[itheta][ip][im] / Frac_events_raw_SM_SMEFT[itheta][ip][im])**2))
            
            # Set the weight per bin
            weight_per_bin = np.zeros_like(poly, dtype=float) # initialise the weight to 0, notably for the case where the denominator is 0
            weight_per_bin_unc = np.zeros_like(poly, dtype=float) # initialise the weight to 0, notably for the case where the denominator is 0
            Mask_N_events_raw_samples = N_events_raw_samples_SMEFT != 0
            Mask_N_events_raw_SM = N_events_raw_SM_SMEFT != 0
            
            weight_per_bin[Mask_N_events_raw_samples] = (poly[Mask_N_events_raw_samples] / N_events_raw_samples_SMEFT[Mask_N_events_raw_samples]) * (xsec_SM/xsec_target) * N_events_raw_SM_SMEFT[Mask_N_events_raw_samples] / C_norm
            weight_per_bin_unc[Mask_N_events_raw_samples & Mask_N_events_raw_SM] =  weight_per_bin[Mask_N_events_raw_samples & Mask_N_events_raw_SM] * np.sqrt((poly_unc[Mask_N_events_raw_samples & Mask_N_events_raw_SM] / poly[Mask_N_events_raw_samples & Mask_N_events_raw_SM])**2 + (N_events_raw_samples_unc_SMEFT[Mask_N_events_raw_samples & Mask_N_events_raw_SM] / N_events_raw_samples_SMEFT[Mask_N_events_raw_samples & Mask_N_events_raw_SM])**2 + (N_events_raw_SM_unc_SMEFT[Mask_N_events_raw_samples & Mask_N_events_raw_SM] / N_events_raw_SM_SMEFT[Mask_N_events_raw_samples & Mask_N_events_raw_SM])**2 + (C_norm_unc / C_norm)**2)
            
            ## Apply the weight event by event
            # Get the bin of the event
            # Find bin indice for each event
            bin_indices_mhh = np.digitize(df_signals['gen_mHH'], bin_edges_mhh_SMEFT) - 1  # digitize begins at 1
            bin_indices_cosThetaStar = np.digitize(np.abs(df_signals['gen_CosThetaStar_HH']), bin_edges_cosThetaStar_SMEFT) - 1  # digitize begins at 1
            bin_indices_pthh = np.digitize(np.abs(df_signals['gen_pT_HH']), bin_edges_pthh_SMEFT) - 1  # digitize begins at 1
            
            # Apply the weights if bin indice is valid # Set weight to 0 if out of binning scheme
            weights_EFT = np.zeros(len(df_signals), dtype=float)
            weights_EFT_unc = np.zeros(len(df_signals), dtype=float)
            valid = (bin_indices_mhh >= 0) & (bin_indices_mhh < nBins_mhh_SMEFT) & (bin_indices_cosThetaStar >= 0) & (bin_indices_cosThetaStar < nBins_cosThetaStar_SMEFT) & (bin_indices_pthh >= 0) & (bin_indices_pthh < nBins_pthh_SMEFT)
            weights_EFT[valid] = weight_per_bin[bin_indices_cosThetaStar[valid], bin_indices_pthh[valid], bin_indices_mhh[valid]]
            weights_EFT_unc[valid] = weight_per_bin_unc[bin_indices_cosThetaStar[valid], bin_indices_pthh[valid], bin_indices_mhh[valid]]
            
            # Add the weight column
            df_signals["weight_SMEFT_CH_{:.2f}_CHBox_{:.2f}_CHD_{:.2f}_CuH_{:.2f}_CHG_{:.2f}".format(CH, CHBox, CHD, CuH, CHG).replace(".","p").replace("-","m")] = weights_EFT
            df_signals["weight_SMEFT_unc_CH_{:.2f}_CHBox_{:.2f}_CHD_{:.2f}_CuH_{:.2f}_CHG_{:.2f}".format(CH, CHBox, CHD, CuH, CHG).replace(".","p").replace("-","m")] = weights_EFT_unc
    
    comment = ""
    if coeffs_from_arxiv:
        comment = "_public"
    else:
        comment = "_private"
    if SM_only:
        comment += "_SMonly"
    if No_SM:
        comment += "_NoSM"
        
    # Save the new parquet file with EFT weights
    correction_type = "_"+correction_type
    if correction_type == "_nominal":
        correction_type =""
    
    outfile_name = "GluGluToHHto2B2Tau_EFTReweighted_{}D{}{}.parquet".format(dim,comment,correction_type)
    output_path = os.path.join(outputDir, args.era, outfile_name)
    exist_or_make(outputDir+args.era)
    df_signals.to_parquet(output_path, index=False)
    print("Saved to: ", output_path)

