# Required Fixes for Reweight_EFT.py

Based on your checklist feedback and inspection of your actual config files, here are the **specific fixes** you need to make to `Reweight_EFT.py`:

---

## ✅ 1. Sample Name Regex - **CORRECT AS-IS**

Your current regex pattern is correct:
```python
pattern_signals_keys = r"^GluGlutoHHto2B2Tau_kl_([0-9]+[pm][0-9]+)_kt_([0-9]+[pm][0-9]+)_c2_([0-9]+[pm][0-9]+)$"
```

This matches your actual sample names from `config/Run3_2022/processes.yaml`:
- ✅ `GluGlutoHHto2B2Tau_kl_0p00_kt_1p00_c2_0p00`
- ✅ `GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_0p10`
- ✅ `GluGlutoHHto2B2Tau_kl_2p45_kt_1p00_c2_0p00`
- etc.

**Note**: The pattern uses lowercase `GluGlutoHH` (not `GluGluToHH`), which matches your datasets.

---

## ⚠️ 2. SM Sample Name - **NEEDS VERIFICATION**

**Current code (lines 124-127):**
```python
if not No_SM:
    signals.append("GluGluToHH")

signal_SM = ["GluGluToHH"]
```

**ACTION REQUIRED:**
Check your `config/Run3_2022/processes.yaml` for the SM sample key. Look for entries like:
- `GluGluToHH` (capital To)
- `GluGlutoHH` (lowercase to) 
- `GGF_HH_SM`
- `ggHH_SM`

**If your SM sample key is different**, update lines 125 and 127:
```python
# Example if your SM key is "GGF_HH_SM":
if not No_SM:
    signals.append("GGF_HH_SM")  # Change this

signal_SM = ["GGF_HH_SM"]  # And this
```

To find your SM sample key:
```bash
grep -i "SM\|GluGlu.*HH" config/Run3_2022/processes.yaml | grep -v "2B2Tau"
```

---

## ⚠️ 3. Systematic Variations - **MUST CHANGE**

**Current code (line 130):**
```python
corrections_types = ["nominal","Et_dependent_ScaleEB_down","Et_dependent_ScaleEB_up",
                     "Et_dependent_ScaleEE_down","Et_dependent_ScaleEE_up",
                     "Et_dependent_Smearing_down","Et_dependent_Smearing_up",
                     "jec_syst_Total_down","jec_syst_Total_up",
                     "jer_syst_down","jer_syst_up"]
```

These are **photon systematics from bbγγ** and will fail for ττ!

**REPLACE with your actual ττ systematics:**

```python
# Option A: If you only have nominal (SAFEST for initial testing)
corrections_types = ["nominal"]

# Option B: If you have systematics, use YOUR folder names
corrections_types = [
    "nominal",
    "jec_Total_up", "jec_Total_down",        # JEC
    "jer_up", "jer_down",                     # JER  
    "tauES_DM0_up", "tauES_DM0_down",        # Tau energy scale
    "tauES_DM1_up", "tauES_DM1_down",
    "tauES_DM10_up", "tauES_DM10_down",
    "eleES_up", "eleES_down",                 # Electron energy scale
    "muES_up", "muES_down",                   # Muon energy scale
    # Add other systematics as needed
]
```

**How to find your systematic folder names:**
```bash
# Check what folders exist in your parquet output directory
ls /path/to/your/parquet/output/
```

**IMPORTANT**: If line 131 `if nominal_only:` is active (default `True`), it will override to `["nominal"]` only, which is **SAFE for testing**.

---

## ⚠️ 4. Gen-Level Variable Names - **CHECK YOUR FILES**

**Current code requires (lines 175-176):**
```python
required_gen_vars = ['gen_mHH', 'gen_CosThetaStar_HH', 'gen_pT_HH']
```

**ACTION REQUIRED:**
Check if your parquet files have these exact names:

```python
# Quick check:
import pandas as pd
df = pd.read_parquet("/path/to/your/GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_0p00.parquet")
print([col for col in df.columns if 'gen' in col.lower() or 'mhh' in col.lower()])
```

**If your variable names are different**, add remapping after line 172:

```python
# After line 172: df_SM = df_local if len(df_SM) == 0 else df_SM.append(df_local)

    # ADD THIS SECTION for variable name remapping:
    # Remap gen-level variable names if they differ
    rename_map = {
        # Add your mappings here:
        # "your_gen_mhh_name": "gen_mHH",
        # "your_gen_costheta_name": "gen_CosThetaStar_HH", 
        # "your_gen_pthh_name": "gen_pT_HH",
    }
    
    # Example remappings (uncomment and adjust if needed):
    # "mhh_gen": "gen_mHH",
    # "gen_mhh": "gen_mHH",
    # "genHH_mass": "gen_mHH",
    # "gen_cosThetaStar": "gen_CosThetaStar_HH",
    # "gen_cosTheta_HH": "gen_CosThetaStar_HH",
    # "gen_pTHH": "gen_pT_HH",
    # "gen_pt_HH": "gen_pT_HH",
    
    for old, new in rename_map.items():
        if old in df_signals.columns and new not in df_signals.columns:
            df_signals[new] = df_signals[old]
        if old in df_SM.columns and new not in df_SM.columns:
            df_SM[new] = df_SM[old]
```

---

## ⚠️ 5. Map Eras File Structure - **CREATE OR VERIFY**

**Current code expects (lines 94-96, 110, 152-153):**
```python
map_eras = read_yaml(map_eras_file)  # Default: "./docs/v2/map_eras.yaml"
list_samples_file = map_eras[run_eras[0]]['list_samples']
dict_samples = read_yaml(list_samples_file)
```

**ACTION REQUIRED:**

### Option A: Create `docs/v2/map_eras.yaml` (RECOMMENDED)

```yaml
# File: docs/v2/map_eras.yaml

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
```

### Option B: Use direct parquet directory

Run with `--input-parquet-dir` flag instead:
```bash
python Reweight_EFT.py \
    -e Run3_2022 \
    -o ./Reweighted_parquets/ \
    --input-parquet-dir /path/to/your/parquet/files/ \
    --nominal-only
```

---

## ⚠️ 6. Parquet Path Structure - **VERIFY**

The script expects `samples[signal]['path']` to point to parquet files.

**Check your `processes.yaml` structure:**

```bash
grep -A5 "GluGlutoHHto2B2Tau_kl_1p00" config/Run3_2022/processes.yaml
```

**If it doesn't have a `path:` field**, you have two options:

### Option A: Add path field to processes.yaml

```yaml
# In config/Run3_2022/processes.yaml
GluGlutoHHto2B2Tau:
  # ... other fields ...
  datasets:
    - GluGlutoHHto2B2Tau_kl_0p00_kt_1p00_c2_0p00
    # Add path for each:
    path: /path/to/parquet/output/
```

### Option B: Create separate samples YAML

Create `config/Run3_2022/samples_for_eft.yaml`:
```yaml
GluGlutoHHto2B2Tau_kl_0p00_kt_1p00_c2_0p00:
  path: /eos/cms/.../Run3_2022/
  
GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_0p00:
  path: /eos/cms/.../Run3_2022/

GluGlutoHHto2B2Tau_kl_2p45_kt_1p00_c2_0p00:
  path: /eos/cms/.../Run3_2022/
  
# SM sample
GluGluToHH:  # Or your SM key name
  path: /eos/cms/.../Run3_2022/
```

Then update `map_eras.yaml`:
```yaml
Run3_2022:
  list_samples: config/Run3_2022/samples_for_eft.yaml
```

---

## ⚠️ 7. External EFT Files - **MUST COPY FROM bbγγ**

**CRITICAL**: These files must exist in your `Analysis/` directory:

### Required Directory Structure:
```
Analysis/
├── Coefficients_EFT/
│   ├── 1D_mhh/
│   │   └── 1000samples_heft_theta_0.0-1.0.txt
│   ├── 1D_mhh_arxiv_2304_01968/
│   │   ├── HEFT_dA_and_A_with_Binning_*.txt
│   │   └── HEFT_CovMat_for_dA_muR_muF_1.txt
│   ├── 2D_cosThetaStar_mhh/
│   │   ├── 1000samples_heft_theta_0.0-0.4.txt
│   │   ├── 1000samples_heft_theta_0.4-0.6.txt
│   │   ├── 1000samples_heft_theta_0.6-0.8.txt
│   │   └── 1000samples_heft_theta_0.8-1.0.txt
│   └── 3D_SMEFT/
│       └── SMEFT_formula_with_error.pkl
├── configs/
│   ├── HEFT_points_out.yaml
│   └── SMEFT_points_out.yaml
└── Normalisation_EFT_reweight/
    ├── 1D_mhh/
    │   └── Run3_2022/
    │       ├── Normalisation_EFT_GluGluToHH.txt
    │       └── Normalisation_EFT_GluGlutoHHto2B2Tau_*.txt
    └── 3D_SMEFT/
        └── Run3_2022/
            └── (same structure)
```

### Copy Commands:
```bash
cd /afs/cern.ch/user/y/yumeng/HH_bbtautau/Analysis/

# Copy EFT coefficient files (universal)
BBGG_PATH="/path/to/HH_bbgg/Analysis"  # Update this!
cp -r ${BBGG_PATH}/Coefficients_EFT/ ./

# Copy config templates
mkdir -p configs
cp ${BBGG_PATH}/configs/HEFT_points_out.yaml configs/
cp ${BBGG_PATH}/configs/SMEFT_points_out.yaml configs/
```

### Generate Normalization Files:
You **must create** these yourself from your raw NanoAOD samples (no cuts!).

See detailed instructions in `EFT_REWEIGHTING_README.md` Section "Normalization Files".

---

## ⚠️ 8. EFT Config Files - **UPDATE CROSS-SECTIONS**

**Files to edit:**
- `configs/HEFT_points_out.yaml`
- `configs/SMEFT_points_out.yaml`

**Check that:**
1. **Keys match your EFT point names** exactly
2. **Cross-sections (`xs:`) are correct** for your generator setup

Example:
```yaml
# configs/HEFT_points_out.yaml
ggHH_kl_1p00_kt_1p00_c2_0p00_cg_0p00_c2g_0p00:
  kl: 1.0
  kt: 1.0
  c2: 0.0
  cg: 0.0
  c2g: 0.0
  xs: 31.05  # ← VERIFY this matches your generator!
```

**How to get correct cross-sections:**
```bash
# From your generator logs or cross-section database
# For Run3 at 13.6 TeV, SM gg→HH is ~34.4 fb
# Update all xs values accordingly
```

---

## 📋 Quick Checklist

Before running `Reweight_EFT.py`:

- [ ] **Check SM sample name** (line 125, 127) matches your `processes.yaml`
- [ ] **Update systematics list** (line 130) or use `--nominal-only` flag
- [ ] **Verify gen variable names** exist in your parquets
- [ ] **Create `docs/v2/map_eras.yaml`** OR use `--input-parquet-dir`
- [ ] **Verify parquet path structure** in your config files
- [ ] **Copy `Coefficients_EFT/`** directory from bbγγ
- [ ] **Copy `configs/*.yaml`** files from bbγγ  
- [ ] **Generate `Normalisation_EFT_reweight/`** files
- [ ] **Update cross-sections** in `configs/HEFT_points_out.yaml`

---

## 🧪 Test Command

Start with this minimal test:

```bash
cd /afs/cern.ch/user/y/yumeng/HH_bbtautau/Analysis/

# Test 1: Check sample names are found
python Reweight_EFT.py \
    -e Run3_2022 \
    -o ./test_output/ \
    --SM-only \
    --nominal-only \
    --HEFT_only \
    -d 1

# If successful, test with all samples
python Reweight_EFT.py \
    -e Run3_2022 \
    -o ./test_output/ \
    --nominal-only \
    --HEFT_only \
    -d 1
```

Look for errors at:
1. **"Signals:"** print - should show your sample names
2. **File reading** - should find all parquet files
3. **Gen variable check** - should not raise ValueError
4. **Coefficient loading** - should not raise FileNotFoundError

---

## 🐛 Common Errors and Fixes

### Error: "FileNotFoundError: Parquet file not found"
**Fix**: Check `samples[signal]['path']` structure (see #6)

### Error: "KeyError: 'GluGluToHH'"  
**Fix**: Update SM sample name (see #2)

### Error: "missing gen-level variables"
**Fix**: Add variable remapping (see #4)

### Error: "FileNotFoundError: Coefficients_EFT/"
**Fix**: Copy from bbγγ repo (see #7)

### Error: "KeyError: 'xs'" in HEFT_points
**Fix**: Update `configs/HEFT_points_out.yaml` structure (see #8)

---

## 📞 Next Steps

1. **Work through checklist** above
2. **Run test command** to identify issues
3. **Fix errors** using this guide
4. **Verify output** has weight columns
5. **Check SM weight** is ~1.0

Good luck! 🚀

