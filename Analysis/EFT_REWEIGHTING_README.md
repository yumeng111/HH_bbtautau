# EFT Reweighting for HH→bbττ Analysis

## Overview

This document explains how to use the `Reweight_EFT_parquet.py` script adapted from the HH→bbγγ analysis for your HH→bbττ analysis. The script applies Effective Field Theory (EFT) reweighting to derive arbitrary HEFT and SMEFT signal points from existing Monte Carlo samples.

## Key Differences from bbγγ Code

### 1. **Sample Names**
- **bbγγ**: `GluGlutoHHto2B2G_kl_X_kt_Y_c2_Z`
- **bbττ**: `GluGlutoHHto2B2Tau_kl_X_kt_Y_c2_Z`

The sample name pattern has been updated to match your τ final state.

### 2. **Output File Names**
- **bbγγ**: `GluGluToHHto2B2G_EFTReweighted_*.parquet`
- **bbττ**: `GluGluToHHto2B2Tau_EFTReweighted_*.parquet`

## Required Modifications in Your Code

### **CRITICAL: Add Generator-Level Variables**

The EFT reweighting requires three generator-level kinematic variables that **must be present** in your parquet files:

1. **`gen_mHH`**: Invariant mass of the di-Higgs system (in GeV)
2. **`gen_CosThetaStar_HH`**: Cosine of the helicity angle in the HH rest frame
3. **`gen_pT_HH`**: Transverse momentum of the di-Higgs system (in GeV)

#### How to Calculate These Variables:

These variables should be calculated at the **tuple production stage** (in your `anaTupleProducer.py` or equivalent). Here's example C++ code to add to your RDataFrame definitions:

```cpp
// Define Gen HH system 4-momentum
df = df.Define("GenHH_p4", R"(
    // Find the two gen H bosons (PDG ID = 25)
    std::vector<int> higgs_indices;
    for(size_t i = 0; i < GenPart_pdgId.size(); i++) {
        if(abs(GenPart_pdgId[i]) == 25 && GenPart_statusFlags[i] & (1 << 13)) { // isLastCopy
            higgs_indices.push_back(i);
        }
    }
    
    if(higgs_indices.size() >= 2) {
        ROOT::Math::PtEtaPhiMVector H1(GenPart_pt[higgs_indices[0]], 
                                        GenPart_eta[higgs_indices[0]], 
                                        GenPart_phi[higgs_indices[0]], 
                                        GenPart_mass[higgs_indices[0]]);
        ROOT::Math::PtEtaPhiMVector H2(GenPart_pt[higgs_indices[1]], 
                                        GenPart_eta[higgs_indices[1]], 
                                        GenPart_phi[higgs_indices[1]], 
                                        GenPart_mass[higgs_indices[1]]);
        return H1 + H2;
    }
    return ROOT::Math::PtEtaPhiMVector(0, 0, 0, 0);
)");

// Calculate gen_mHH
df = df.Define("gen_mHH", "GenHH_p4.M()");

// Calculate gen_pT_HH
df = df.Define("gen_pT_HH", "GenHH_p4.Pt()");

// Calculate gen_CosThetaStar_HH
df = df.Define("gen_CosThetaStar_HH", R"(
    // cos(theta*) in HH rest frame
    // This is the angle between one H and the beam axis in the HH CM frame
    std::vector<int> higgs_indices;
    for(size_t i = 0; i < GenPart_pdgId.size(); i++) {
        if(abs(GenPart_pdgId[i]) == 25 && GenPart_statusFlags[i] & (1 << 13)) {
            higgs_indices.push_back(i);
        }
    }
    
    if(higgs_indices.size() >= 2) {
        ROOT::Math::PtEtaPhiMVector H1(GenPart_pt[higgs_indices[0]], 
                                        GenPart_eta[higgs_indices[0]], 
                                        GenPart_phi[higgs_indices[0]], 
                                        GenPart_mass[higgs_indices[0]]);
        ROOT::Math::PtEtaPhiMVector HH = GenHH_p4;
        
        // Boost H1 to HH rest frame
        ROOT::Math::Boost boost_to_HH_frame(HH.BoostToCM());
        auto H1_boosted = boost_to_HH_frame(H1);
        
        // CosThetaStar is cos of angle between H1 and beam axis (z-axis)
        return H1_boosted.Pz() / H1_boosted.P();
    }
    return 0.0;
)");
```

#### Alternative Python Implementation (for post-processing):

If you prefer to add these variables to existing parquet files:

```python
import pandas as pd
import numpy as np
from ROOT import Math

def calculate_gen_HH_variables(parquet_file):
    """Add gen-level HH variables to parquet file"""
    df = pd.read_parquet(parquet_file)
    
    # Assuming you have GenPart branches in your parquet
    # Extract the two Higgs bosons
    # ... (implement the same logic as above in Python/NumPy)
    
    # Save back to parquet
    df.to_parquet(parquet_file)
```

### **Where to Add These Modifications:**

1. **In `FLAF/AnaProd/anaTupleProducer.py`** (or your equivalent):
   - Add the above C++ definitions in the `defineGenVariables()` function
   - Make sure these variables are added to `colToSave` list

2. **In `AnaProd/baseline.py`**:
   - If you have a `DefineGenObjects()` function, add these calculations there

3. **Make sure to regenerate your tuples** after adding these variables!

## Required Directory Structure

You need to create the following directory structure in your `Analysis/` folder:

```
Analysis/
├── Coefficients_EFT/
│   ├── 1D_mhh/
│   │   └── 1000samples_heft_theta_0.0-1.0.txt
│   ├── 1D_mhh_arxiv_2304_01968/
│   │   ├── HEFT_dA_and_A_with_Binning_250_1050_41_Variable_Bins_1200_1400_muR_muF_1.txt
│   │   └── HEFT_CovMat_for_dA_muR_muF_1.txt
│   ├── 2D_cosThetaStar_mhh/
│   │   ├── 1000samples_heft_theta_0.0-0.4.txt
│   │   ├── 1000samples_heft_theta_0.4-0.6.txt
│   │   ├── 1000samples_heft_theta_0.6-0.8.txt
│   │   └── 1000samples_heft_theta_0.8-1.0.txt
│   └── 3D_SMEFT/
│       └── SMEFT_formula_with_error.pkl
├── Normalisation_EFT_reweight/
│   ├── 1D_mhh/
│   │   └── Run3_2022/
│   │       ├── Normalisation_EFT_GluGluToHH.txt
│   │       └── Normalisation_EFT_GluGlutoHHto2B2Tau_*.txt
│   └── 3D_SMEFT/
│       └── Run3_2022/
│           └── (same as above)
├── configs/
│   ├── HEFT_points_out.yaml
│   ├── SMEFT_points_out.yaml
│   └── variables.yaml (optional)
└── Reweight_EFT_parquet.py
```

### **How to Get These Files:**

You should **copy** these files from the HH→bbγγ repository:
- The `Coefficients_EFT/` directory contains the EFT polynomial coefficients (same for all HH decay channels)
- The `configs/*.yaml` files define which EFT points to generate

```bash
# From the bbgg repository location
cp -r Coefficients_EFT/ /path/to/HH_bbtautau/Analysis/
cp -r configs/HEFT_points_out.yaml configs/SMEFT_points_out.yaml /path/to/HH_bbtautau/Analysis/configs/
```

### **Normalisation Files:**

You need to create normalisation files that contain the number of events in each kinematic bin **before any selection**. These should be generated from your raw NanoAOD files:

```python
# Example script to generate normalisation files
import pandas as pd
import numpy as np

def generate_normalisation_file(nanoaod_file, output_file, sample_name):
    """Generate normalisation histogram from NanoAOD"""
    # Read gen-level info (no selection!)
    # Calculate histograms in (mHH, cosThetaStar, pT_HH) bins
    # Save to text file
    pass  # Implement based on your framework
```

## Configuration Files Required

### 1. `configs/HEFT_points_out.yaml`

Example structure:
```yaml
ggHH_kl_1p00_kt_1p00_c2_0p00_cg_0p00_c2g_0p00:
  kl: 1.0
  kt: 1.0
  c2: 0.0
  cg: 0.0
  c2g: 0.0
  xs: 31.05  # Cross-section in fb

ggHH_kl_0p00_kt_1p00_c2_0p00_cg_0p00_c2g_0p00:
  kl: 0.0
  kt: 1.0
  c2: 0.0
  cg: 0.0
  c2g: 0.0
  xs: 63.42

# ... add more HEFT points
```

### 2. `configs/SMEFT_points_out.yaml`

Example structure:
```yaml
ggHH_CH_0p00_CHBox_0p00_CHD_0p00_CuH_0p00_CHG_0p00:
  CH: 0.0
  CHBox: 0.0
  CHD: 0.0
  CuH: 0.0
  CHG: 0.0
  xs: 31.05  # SM cross-section

ggHH_CH_1p00_CHBox_0p00_CHD_0p00_CuH_0p00_CHG_0p00:
  CH: 1.0
  CHBox: 0.0
  CHD: 0.0
  CuH: 0.0
  CHG: 0.0
  xs: 45.2

# ... add more SMEFT points
```

### 3. `docs/v2/map_eras.yaml` (Optional)

This file maps era names to sample configuration files:

```yaml
Run3_2022:
  list_samples: config/Run3_2022/processes.yaml

Run3_2022postEE:
  list_samples: config/Run3_2022EE/processes.yaml

Run3_2023:
  list_samples: config/Run3_2023/processes.yaml
```

## Usage Examples

### Basic Usage (1D HEFT reweighting):

```bash
cd Analysis/
python Reweight_EFT_parquet.py \
    -e Run3_2022 \
    -o ./Reweighted_parquets/ \
    -d 1 \
    --nominal-only
```

### 2D HEFT Reweighting:

```bash
python Reweight_EFT_parquet.py \
    -e Run3_2022 \
    -o ./Reweighted_parquets/ \
    -d 2 \
    --nominal-only
```

### HEFT + SMEFT Reweighting:

```bash
python Reweight_EFT_parquet.py \
    -e Run3_2022 \
    -o ./Reweighted_parquets/ \
    -d 1 \
    --nominal-only
    # SMEFT weights are added by default (remove --HEFT_only flag)
```

### With Systematics:

```bash
python Reweight_EFT_parquet.py \
    -e Run3_2022 \
    -o ./Reweighted_parquets/ \
    -d 1
    # Removes --nominal-only to process all systematic variations
```

### Direct Input (without map_eras file):

```bash
python Reweight_EFT_parquet.py \
    -e Run3_2022 \
    -o ./Reweighted_parquets/ \
    -d 1 \
    --input-parquet-dir /path/to/your/parquet/files/ \
    --nominal-only
```

## Output

The script produces parquet files with added weight columns:

- **HEFT weights**: `weight_EFT_kl_1p00_kt_1p00_c2_0p00_cg_0p00_c2g_0p00` (and corresponding `weight_EFT_unc_*` for uncertainties)
- **SMEFT weights**: `weight_SMEFT_CH_0p00_CHBox_0p00_CHD_0p00_CuH_0p00_CHG_0p00` (and corresponding `weight_SMEFT_unc_*`)

Output file naming:
```
GluGluToHHto2B2Tau_EFTReweighted_1D_private.parquet
GluGluToHHto2B2Tau_EFTReweighted_2D_private.parquet
GluGluToHHto2B2Tau_EFTReweighted_1D_public.parquet  (with --coeffs-from_arxiv-2304-01968)
```

## Physics Background

### EFT Theory

The script implements the analytical reweighting method described in:
- **HEFT (1D/2D)**: [arXiv:2304.01968](https://arxiv.org/abs/2304.01968) - "A practical guide to Higgs boson pair production and their impact on direct measurements"
- **SMEFT (3D)**: [arXiv:2502.20976](https://arxiv.org/abs/2502.20976)

### Reweighting Formula

The event weight for a target EFT point is:

```
w_i(λ) = [A(x_i, λ) / A(x_i, λ_SM)] × [N_SM(x_i) / N_input(x_i)] × [σ_SM / σ_target] × [1 / C_norm]
```

Where:
- `A(x, λ)`: Differential cross-section parameterized as polynomial in EFT parameters
- `x_i`: Kinematic bin (mHH, cosThetaStar, pT_HH)
- `N_SM(x_i)`: Number of SM events in bin i (from normalisation files)
- `N_input(x_i)`: Number of input sample events in bin i
- `C_norm`: Normalization constant to preserve total cross-section

## Common Issues and Solutions

### 1. **Missing gen-level variables**
```
ERROR: The following required gen-level variables are missing: ['gen_mHH', 'gen_CosThetaStar_HH', 'gen_pT_HH']
```
**Solution**: Add these variables to your tuple production as described above.

### 2. **Missing coefficient files**
```
FileNotFoundError: Coefficients_EFT/1D_mhh/1000samples_heft_theta_0.0-1.0.txt
```
**Solution**: Copy the `Coefficients_EFT/` directory from the bbγγ repository.

### 3. **Missing normalization files**
```
FileNotFoundError: Normalisation_EFT_reweight/1D_mhh/Run3_2022/Normalisation_EFT_GluGluToHH.txt
```
**Solution**: Generate these files from your raw NanoAOD samples (no selection applied).

### 4. **Sample name mismatch**
```
KeyError: 'GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_0p00'
```
**Solution**: Check that your sample names in the parquet files match the pattern expected by the script. Update the regex pattern if needed.

## Important Notes

1. **Cross-sections**: Make sure the cross-sections in `HEFT_points_out.yaml` and `SMEFT_points_out.yaml` are correct for your generator setup.

2. **Normalization is critical**: The normalisation files must be generated from samples **without any selection cuts** to ensure correct normalization.

3. **The EFT coefficients are universal**: The polynomial coefficients in `Coefficients_EFT/` are the same for all HH decay channels (they depend only on the HH production mechanism, not the decay).

4. **Binning scheme**: The kinematic binning (mHH, cosThetaStar, pT_HH) is optimized for the EFT reweighting and should not be changed unless you regenerate the coefficient files.

5. **Dependencies**: Make sure you have:
   - `pandas`
   - `numpy`
   - `pyyaml`

## Testing

Test the script with a small subset of data first:

```bash
# Test with SM sample only
python Reweight_EFT_parquet.py \
    -e Run3_2022 \
    -o ./test_output/ \
    -d 1 \
    --SM-only \
    --nominal-only
```

Check the output:
- File should exist in `./test_output/Run3_2022/`
- Should contain new weight columns
- Weights should be ~ 1.0 for SM point

## Contact

For questions about the EFT theory implementation, refer to the original bbγγ analysis team or the papers cited above.

For bbtautau-specific questions, contact your analysis team.

