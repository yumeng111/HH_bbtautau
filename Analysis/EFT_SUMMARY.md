# EFT Reweighting for HH→bbττ - Complete Setup Guide

## What Has Been Done

I have adapted the EFT reweighting script from the HH→bbγγ analysis to your HH→bbττ analysis. The following files have been created:

### 1. Main Script
- **`Reweight_EFT_parquet.py`** - The main EFT reweighting script adapted for bbtautau

### 2. Documentation
- **`EFT_REWEIGHTING_README.md`** - Comprehensive documentation explaining the physics, usage, and troubleshooting

### 3. Configuration Examples
- **`configs_example/HEFT_points_out.yaml`** - Example HEFT parameter points configuration
- **`configs_example/SMEFT_points_out.yaml`** - Example SMEFT parameter points configuration

### 4. Helper Script
- **`add_gen_HH_variables.py`** - Utility script to add required gen-level variables to existing files

## Quick Start Checklist

### Step 1: Copy Required Files from bbγγ Repository

You need to obtain these files from the HH_bbgg repository (they are the same for all HH channels):

```bash
# From the HH_bbgg repository
BBGG_REPO="/path/to/HH_bbgg"  # Update this path

cd /afs/cern.ch/user/y/yumeng/HH_bbtautau/Analysis/

# Copy EFT coefficient files (universal for all HH channels)
cp -r ${BBGG_REPO}/Coefficients_EFT/ ./

# Copy normalization files template (you'll need to regenerate for your samples)
# cp -r ${BBGG_REPO}/Normalisation_EFT_reweight/ ./  # Optional template

# Copy or adapt configuration files
mkdir -p configs
cp ${BBGG_REPO}/configs/HEFT_points_out.yaml configs/
cp ${BBGG_REPO}/configs/SMEFT_points_out.yaml configs/
```

The directory structure should look like:
```
Analysis/
├── Coefficients_EFT/
│   ├── 1D_mhh/
│   ├── 1D_mhh_arxiv_2304_01968/
│   ├── 2D_cosThetaStar_mhh/
│   └── 3D_SMEFT/
├── configs/
│   ├── HEFT_points_out.yaml
│   └── SMEFT_points_out.yaml
├── Reweight_EFT_parquet.py
└── EFT_REWEIGHTING_README.md
```

### Step 2: Add Generator-Level Variables to Your Tuples

**CRITICAL**: The EFT reweighting requires three gen-level variables:

- `gen_mHH` - di-Higgs invariant mass
- `gen_CosThetaStar_HH` - helicity angle in HH rest frame
- `gen_pT_HH` - di-Higgs transverse momentum

#### Option A: Add During Tuple Production (Recommended)

Add this code to your tuple producer (e.g., in `FLAF/AnaProd/anaTupleProducer.py` or equivalent):

```python
# In your DefineGenVariables function or similar location:

ROOT.gInterpreter.Declare("""
    struct GenHHVars {
        float gen_mHH;
        float gen_CosThetaStar_HH;
        float gen_pT_HH;
    };
    
    GenHHVars CalculateGenHHVariables(
        const ROOT::VecOps::RVec<float>& pt,
        const ROOT::VecOps::RVec<float>& eta,
        const ROOT::VecOps::RVec<float>& phi,
        const ROOT::VecOps::RVec<float>& mass,
        const ROOT::VecOps::RVec<int>& pdgId,
        const ROOT::VecOps::RVec<int>& statusFlags
    ) {
        GenHHVars result{0.0f, 0.0f, 0.0f};
        
        // Find two Higgs bosons (PDG ID = 25, isLastCopy)
        std::vector<int> higgs_indices;
        for(size_t i = 0; i < pdgId.size(); i++) {
            if(abs(pdgId[i]) == 25 && (statusFlags[i] & (1 << 13))) {
                higgs_indices.push_back(i);
            }
        }
        
        if(higgs_indices.size() < 2) return result;
        
        // Build 4-vectors
        ROOT::Math::PtEtaPhiMVector H1(pt[higgs_indices[0]], eta[higgs_indices[0]], 
                                       phi[higgs_indices[0]], mass[higgs_indices[0]]);
        ROOT::Math::PtEtaPhiMVector H2(pt[higgs_indices[1]], eta[higgs_indices[1]], 
                                       phi[higgs_indices[1]], mass[higgs_indices[1]]);
        ROOT::Math::PtEtaPhiMVector HH = H1 + H2;
        
        result.gen_mHH = HH.M();
        result.gen_pT_HH = HH.Pt();
        
        // Calculate cos(theta*) in HH rest frame
        ROOT::Math::Boost boost_to_HH_frame(HH.BoostToCM());
        auto H1_boosted = boost_to_HH_frame(H1);
        float p_mag = std::sqrt(H1_boosted.Px()*H1_boosted.Px() + 
                               H1_boosted.Py()*H1_boosted.Py() + 
                               H1_boosted.Pz()*H1_boosted.Pz());
        if(p_mag > 0) result.gen_CosThetaStar_HH = H1_boosted.Pz() / p_mag;
        
        return result;
    }
""")

# In your RDataFrame processing:
df = df.Define("GenHHVars", 
               "CalculateGenHHVariables(GenPart_pt, GenPart_eta, GenPart_phi, "
               "GenPart_mass, GenPart_pdgId, GenPart_statusFlags)")
df = df.Define("gen_mHH", "GenHHVars.gen_mHH")
df = df.Define("gen_CosThetaStar_HH", "GenHHVars.gen_CosThetaStar_HH")
df = df.Define("gen_pT_HH", "GenHHVars.gen_pT_HH")

# Add these to your colToSave list:
colToSave.extend(["gen_mHH", "gen_CosThetaStar_HH", "gen_pT_HH"])
```

Then **regenerate your tuples** for signal samples.

#### Option B: Add to Existing Files (Post-processing)

If you already have tuples and don't want to regenerate, use the helper script:

```bash
# For ROOT files
python add_gen_HH_variables.py \
    --input /path/to/input.root \
    --output /path/to/output.root \
    --tree Events \
    --format root

# For parquet files (if applicable)
python add_gen_HH_variables.py \
    --input /path/to/input.parquet \
    --output /path/to/output.parquet \
    --format parquet
```

### Step 3: Generate Normalization Files

The normalization files contain event counts in kinematic bins **without any selection cuts**. These are essential for correct EFT reweighting.

Create this directory structure:
```
Normalisation_EFT_reweight/
├── 1D_mhh/
│   └── Run3_2022/
│       ├── Normalisation_EFT_GluGluToHH.txt
│       └── Normalisation_EFT_GluGlutoHHto2B2Tau_*.txt
└── 3D_SMEFT/
    └── Run3_2022/
        └── (same as above)
```

Example script to generate these files:

```python
import ROOT
import numpy as np

def generate_normalisation(input_file, output_file, dim=1):
    """Generate normalisation histogram from NanoAOD/tuples"""
    df = ROOT.RDataFrame("Events", input_file)
    
    # Make sure gen variables exist
    df = df.Filter("gen_mHH > 0", "HasGenHH")
    
    # Define bin edges (same as in Reweight_EFT_parquet.py)
    if dim == 1:
        bin_edges_mhh = np.array([250,270,290,310,330,350,370,390,410,430,450,
                                  470,490,510,530,550,570,590,610,630,650,670,
                                  690,710,730,750,800,850,900,950,1000,1050,
                                  1150,1200,1300,1400,1500,1600,1800,2000,3000])
        
        # Create histogram (NO SELECTION!)
        h = df.Histo1D(("h", "h", len(bin_edges_mhh)-1, bin_edges_mhh), "gen_mHH")
        
        # Save to text file
        with open(output_file, 'w') as f:
            f.write("# Normalisation histogram (no selection)\n")
            for i in range(len(bin_edges_mhh)-1):
                f.write(f"{h.GetBinContent(i+1)}\n")
    
    elif dim == 3:  # SMEFT 3D
        # Similar but for 3D histogram
        # ... (implement 3D histogram)
        pass

# Run for each signal sample
samples = ["GluGluToHH", "GluGlutoHHto2B2Tau_kl_1p00_kt_1p00_c2_0p00"]
for sample in samples:
    generate_normalisation(
        f"/path/to/{sample}.root",
        f"Normalisation_EFT_reweight/1D_mhh/Run3_2022/Normalisation_EFT_{sample}.txt",
        dim=1
    )
```

**Important**: 
- Generate normalization from raw samples (no cuts!)
- Use the **exact same binning** as in the reweighting script
- Create files for all eras you'll process

### Step 4: Update Configuration Files

Edit `configs/HEFT_points_out.yaml` and `configs/SMEFT_points_out.yaml`:

1. **Verify cross-sections** match your generator predictions
2. **Add/remove EFT points** based on your analysis needs
3. **Check parameter ranges** are appropriate for your benchmarks

Example cross-sections for 13.6 TeV (update as needed):
```yaml
# HEFT SM point at 13.6 TeV
ggHH_kl_1p00_kt_1p00_c2_0p00_cg_0p00_c2g_0p00:
  kl: 1.0
  kt: 1.0
  c2: 0.0
  cg: 0.0
  c2g: 0.0
  xs: 34.43  # Update with your generator value!
```

### Step 5: Run the EFT Reweighting

Basic command:
```bash
cd /afs/cern.ch/user/y/yumeng/HH_bbtautau/Analysis/

python Reweight_EFT_parquet.py \
    -e Run3_2022 \
    -o ./Reweighted_parquets/ \
    -d 1 \
    --nominal-only
```

This will:
1. Read your signal parquet files
2. Calculate EFT weights for all points in `configs/HEFT_points_out.yaml` (and SMEFT if not using `--HEFT_only`)
3. Save new parquet files with added weight columns

### Step 6: Verify Output

Check the output file:
```python
import pandas as pd

df = pd.read_parquet("Reweighted_parquets/Run3_2022/GluGluToHHto2B2Tau_EFTReweighted_1D_private.parquet")

# Check that weight columns exist
print(df.columns)
# Should see: weight_EFT_kl_1p00_kt_1p00_c2_0p00_cg_0p00_c2g_0p00, etc.

# Check SM point weight (should be ~1)
print(df["weight_EFT_kl_1p00_kt_1p00_c2_0p00_cg_0p00_c2g_0p00"].describe())
```

## Key Changes from bbγγ Code

| Aspect | bbγγ | bbττ |
|--------|------|------|
| Sample name pattern | `GluGlutoHHto2B2G_*` | `GluGlutoHHto2B2Tau_*` |
| Output file name | `*2B2G_EFTReweighted*` | `*2B2Tau_EFTReweighted*` |
| EFT coefficients | (same) | (same) - Universal for HH production |
| Gen-level variables | (same) | (same) - Based on HH system, not decay |
| Kinematic binning | (same) | (same) - Optimized for HH kinematics |

## What You Need to Do

### Immediate Actions:
1. ✅ Copy `Coefficients_EFT/` from bbγγ repository
2. ✅ Copy or adapt `configs/HEFT_points_out.yaml` and `configs/SMEFT_points_out.yaml`
3. ⚠️ **Add gen-level variables** to your tuple production (CRITICAL!)
4. ⚠️ **Regenerate tuples** for signal samples
5. ⚠️ **Generate normalization files** from raw samples

### Before Running:
6. Update cross-sections in config files to match your generator
7. Verify sample names match your naming convention
8. Test on a small subset first

### After Running:
9. Validate output weights (SM point should be ~1.0)
10. Integrate weights into your analysis workflow
11. Update your statistical inference to use EFT weights

## Common Issues

### "Missing gen-level variables"
→ Add `gen_mHH`, `gen_CosThetaStar_HH`, `gen_pT_HH` to your tuples

### "FileNotFoundError: Coefficients_EFT/"
→ Copy from bbγγ repository

### "FileNotFoundError: Normalisation_EFT_reweight/"
→ Generate normalization files from raw samples (no cuts!)

### "Sample name not found"
→ Check the regex pattern in line 119 of `Reweight_EFT_parquet.py`

## Additional Resources

- **Full Documentation**: See `EFT_REWEIGHTING_README.md`
- **Physics Background**: arXiv:2304.01968 (HEFT), arXiv:2502.20976 (SMEFT)
- **Helper Script**: `add_gen_HH_variables.py` for post-processing
- **Example Configs**: `configs_example/` directory

## Questions?

If you encounter issues:
1. Check `EFT_REWEIGHTING_README.md` for detailed troubleshooting
2. Verify all required files are present
3. Test with `--SM-only` flag first
4. Check that gen-level variables are correctly calculated

Good luck with your EFT reweighting! 🚀

