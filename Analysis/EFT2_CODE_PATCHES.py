"""
Code patches to apply to Reweight_EFT.py based on checklist feedback

Copy the relevant sections below and paste into your Reweight_EFT.py file
"""

# ============================================================================
# PATCH 1: Gen Variable Name Remapping (Insert after line 172)
# ============================================================================
# Location: After df_SM concatenation, before gen variable check

"""
    # Remap gen-level variable names if they differ from expected names
    # Adjust this mapping based on your actual parquet column names
    rename_map = {
        # Common alternative names (uncomment the ones that match your files):
        # "mhh_gen": "gen_mHH",
        # "gen_mhh": "gen_mHH",
        # "genHH_mass": "gen_mHH",
        # "gen_m_HH": "gen_mHH",
        # "HH_mass": "gen_mHH",
        
        # "gen_cosThetaStar": "gen_CosThetaStar_HH",
        # "gen_cosTheta_HH": "gen_CosThetaStar_HH",
        # "cosThetaStar_HH": "gen_CosThetaStar_HH",
        # "gen_abs_cosTheta_HH": "gen_CosThetaStar_HH",  # If you stored absolute value
        
        # "gen_pTHH": "gen_pT_HH",
        # "gen_pt_HH": "gen_pT_HH", 
        # "gen_ptHH": "gen_pT_HH",
        # "HH_pt": "gen_pT_HH",
    }
    
    # Apply remapping to both dataframes
    for old, new in rename_map.items():
        if old in df_signals.columns and new not in df_signals.columns:
            print(f"  Remapping: {old} -> {new} in df_signals")
            df_signals[new] = df_signals[old]
        if old in df_SM.columns and new not in df_SM.columns:
            print(f"  Remapping: {old} -> {new} in df_SM")
            df_SM[new] = df_SM[old]
"""

# ============================================================================
# PATCH 2: ττ Systematics List (Replace line 130)
# ============================================================================
# Location: Replace the photon systematics with tau systematics

# OPTION A: Nominal only (safest for testing)
corrections_types_NOMINAL_ONLY = ["nominal"]

# OPTION B: With systematics (adjust to match your folder names)
corrections_types_WITH_SYSTEMATICS = [
    "nominal",
    # JEC/JER
    "jec_Total_up", "jec_Total_down",
    "jer_up", "jer_down",
    # Tau energy scale by decay mode
    "tauES_DM0_up", "tauES_DM0_down",
    "tauES_DM1_up", "tauES_DM1_down", 
    "tauES_DM10_up", "tauES_DM10_down",
    "tauES_DM11_up", "tauES_DM11_down",
    # Electron/Muon energy scales
    "eleES_up", "eleES_down",
    "muES_up", "muES_down",
    # MET
    "met_unclustered_up", "met_unclustered_down",
    # Tau ID uncertainties
    "tauID_sf_up", "tauID_sf_down",
    # Add other systematics as needed
]

# To use: Replace line 130 with one of the above

# ============================================================================
# PATCH 3: SM Sample Name Fix (Replace lines 124-127)
# ============================================================================
# Location: After signals list is created

# First, FIND your SM sample name in processes.yaml:
# grep -E "^[A-Za-z_]+.*HH.*:" config/Run3_2022/processes.yaml | grep -v "2B2Tau"

# Common possibilities:
SM_sample_option_1 = "GluGluToHH"        # Capital 'To' (common)
SM_sample_option_2 = "GluGlutoHH"        # Lowercase 'to'
SM_sample_option_3 = "GGF_HH_SM"         # Alternative naming
SM_sample_option_4 = "ggHH_SM"           # Short naming

# Once you find yours, replace lines 124-127 with:
"""
if not No_SM:
    signals.append("YOUR_SM_SAMPLE_NAME_HERE")  # ← Change this

signal_SM = ["YOUR_SM_SAMPLE_NAME_HERE"]  # ← Change this
signals_tot = list(np.unique(signals + signal_SM)) if not SM_only else signal_SM
"""

# ============================================================================
# PATCH 4: Create map_eras.yaml file
# ============================================================================
# Location: Create new file at docs/v2/map_eras.yaml

map_eras_yaml_content = """
# File: docs/v2/map_eras.yaml
# Maps era names to their sample configuration files

Run3_2022:
  list_samples: config/Run3_2022/processes.yaml

Run3_2022postEE:
  list_samples: config/Run3_2022EE/processes.yaml
  
Run3_2022preEE:
  list_samples: config/Run3_2022/processes.yaml

Run3_2023:
  list_samples: config/Run3_2023/processes.yaml

Run3_2023postBPix:
  list_samples: config/Run3_2023/processes.yaml

Run3_2023preBPix:
  list_samples: config/Run3_2023BPix/processes.yaml
"""

# To create: Save above content to docs/v2/map_eras.yaml

# ============================================================================
# PATCH 5: Alternative - Create separate samples YAML for EFT
# ============================================================================
# If your processes.yaml doesn't have 'path' field, create this instead

samples_for_eft_yaml_template = """
# File: config/Run3_2022/samples_for_eft.yaml
# Parquet file paths for EFT reweighting

# BSM signal samples
GluGlutoHHto2B2Tau_kl_0p00_kt_1p00_c2_0p00:
  path: /eos/cms/store/group/..../Run3_2022/nominal/

GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_0p00:
  path: /eos/cms/store/group/..../Run3_2022/nominal/

GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_0p10:
  path: /eos/cms/store/group/..../Run3_2022/nominal/

GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_0p35:
  path: /eos/cms/store/group/..../Run3_2022/nominal/

GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_3p00:
  path: /eos/cms/store/group/..../Run3_2022/nominal/

GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_m2p00:
  path: /eos/cms/store/group/..../Run3_2022/nominal/

GluGlutoHHto2B2Tau_kl_2p45_kt_1p00_c2_0p00:
  path: /eos/cms/store/group/..../Run3_2022/nominal/

GluGlutoHHto2B2Tau_kl_5p00_kt_1p00_c2_0p00:
  path: /eos/cms/store/group/..../Run3_2022/nominal/

# SM sample (update key name to match your processes.yaml)
GluGluToHH:  # ← Change if your SM sample has different name
  path: /eos/cms/store/group/..../Run3_2022/nominal/
"""

# Then update map_eras.yaml to point to this file:
map_eras_with_custom_samples = """
Run3_2022:
  list_samples: config/Run3_2022/samples_for_eft.yaml  # ← Point to custom file
"""

# ============================================================================
# PATCH 6: Debug Print to Find SM Sample Name
# ============================================================================
# Insert after line 112 to debug what sample names are found

debug_print_samples = """
    # DEBUG: Print all sample keys found
    print("\\n=== DEBUG: Sample keys in dict_samples ===")
    for key in dict_samples.keys():
        print(f"  {key}")
    print("=" * 50 + "\\n")
"""

# ============================================================================
# PATCH 7: Flexible Path Extraction
# ============================================================================
# Replace line 159 if 'path' field might be nested or missing

flexible_path_extraction = """
            # Flexible path extraction
            if isinstance(samples[signal], dict):
                if 'path' in samples[signal]:
                    path_cat = samples[signal]['path']
                elif 'datasets' in samples[signal] and len(samples[signal]['datasets']) > 0:
                    # Try to construct path from dataset names
                    path_cat = args.input_parquet_dir if args.input_parquet_dir else "./output/parquets/"
                    print(f"  WARNING: No 'path' field for {signal}, using: {path_cat}")
                else:
                    raise ValueError(f"Cannot find 'path' for sample {signal} in config")
            else:
                # samples[signal] might be a string path directly
                path_cat = samples[signal]
"""

# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

usage_instructions = """
HOW TO APPLY THESE PATCHES:

1. SM Sample Name (PATCH 3):
   - Run: grep -E "^[A-Za-z_]+.*HH.*:" config/Run3_2022/processes.yaml | grep -v "2B2Tau"
   - Find your SM key
   - Update lines 124-127 in Reweight_EFT.py

2. Systematics (PATCH 2):
   - Replace line 130 with corrections_types_NOMINAL_ONLY (for testing)
   - Or with corrections_types_WITH_SYSTEMATICS (after adjusting names)

3. Gen Variables (PATCH 1):
   - Check your parquet column names
   - Uncomment relevant mappings in rename_map
   - Insert after line 172

4. Map Eras File (PATCH 4):
   - Create docs/v2/map_eras.yaml with content from PATCH 4
   - OR use PATCH 5 to create custom samples YAML

5. Path Extraction (PATCH 7):
   - Only if you get "KeyError: 'path'" error
   - Replace line 159 with flexible_path_extraction code

6. Debug (PATCH 6):
   - If confused about sample names
   - Insert after line 112 to see what's found

TEST AFTER EACH PATCH:
python Reweight_EFT.py -e Run3_2022 -o ./test/ --SM-only --nominal-only -d 1
"""

print(usage_instructions)

