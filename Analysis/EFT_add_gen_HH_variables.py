#!/usr/bin/env python3
"""
Helper script to add generator-level HH variables to existing ROOT/parquet files
These variables are required for EFT reweighting.

Variables added:
- gen_mHH: invariant mass of di-Higgs system
- gen_CosThetaStar_HH: cosine of helicity angle in HH rest frame  
- gen_pT_HH: transverse momentum of di-Higgs system

Usage:
    python add_gen_HH_variables.py --input input.root --output output.root --tree Events
    
Or for parquet:
    python add_gen_HH_variables.py --input input.parquet --output output.parquet --format parquet
"""

import argparse
import sys
import numpy as np

def add_gen_variables_root(input_file, output_file, tree_name="Events"):
    """Add gen HH variables to ROOT file using RDataFrame"""
    import ROOT
    
    # Load the input file
    df = ROOT.RDataFrame(tree_name, input_file)
    
    # Check if GenPart branches exist
    cols = df.GetColumnNames()
    required_cols = ["GenPart_pt", "GenPart_eta", "GenPart_phi", "GenPart_mass", 
                     "GenPart_pdgId", "GenPart_statusFlags"]
    
    for col in required_cols:
        if col not in cols:
            print(f"ERROR: Required branch '{col}' not found in input file!")
            sys.exit(1)
    
    # Define C++ code for calculations
    ROOT.gInterpreter.Declare("""
    #include <vector>
    #include <cmath>
    
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
        
        // Find the two Higgs bosons (PDG ID = 25)
        // Use isLastCopy flag (bit 13 of statusFlags)
        std::vector<int> higgs_indices;
        for(size_t i = 0; i < pdgId.size(); i++) {
            if(abs(pdgId[i]) == 25 && (statusFlags[i] & (1 << 13))) {
                higgs_indices.push_back(i);
            }
        }
        
        if(higgs_indices.size() < 2) {
            // Return zeros if we don't find two Higgs bosons
            return result;
        }
        
        // Build 4-vectors for the two Higgs bosons
        ROOT::Math::PtEtaPhiMVector H1(
            pt[higgs_indices[0]], 
            eta[higgs_indices[0]], 
            phi[higgs_indices[0]], 
            mass[higgs_indices[0]]
        );
        
        ROOT::Math::PtEtaPhiMVector H2(
            pt[higgs_indices[1]], 
            eta[higgs_indices[1]], 
            phi[higgs_indices[1]], 
            mass[higgs_indices[1]]
        );
        
        // HH system 4-vector
        ROOT::Math::PtEtaPhiMVector HH = H1 + H2;
        
        // Calculate gen_mHH
        result.gen_mHH = HH.M();
        
        // Calculate gen_pT_HH
        result.gen_pT_HH = HH.Pt();
        
        // Calculate gen_CosThetaStar_HH
        // This is the cosine of the angle between H1 and the beam axis (z)
        // in the HH rest frame
        ROOT::Math::Boost boost_to_HH_frame(HH.BoostToCM());
        auto H1_boosted = boost_to_HH_frame(H1);
        
        // cos(theta*) = pz / |p|
        float p_mag = std::sqrt(
            H1_boosted.Px()*H1_boosted.Px() + 
            H1_boosted.Py()*H1_boosted.Py() + 
            H1_boosted.Pz()*H1_boosted.Pz()
        );
        
        if(p_mag > 0) {
            result.gen_CosThetaStar_HH = H1_boosted.Pz() / p_mag;
        }
        
        return result;
    }
    """)
    
    # Define the new columns
    df = df.Define("GenHHVars", 
                   "CalculateGenHHVariables(GenPart_pt, GenPart_eta, GenPart_phi, "
                   "GenPart_mass, GenPart_pdgId, GenPart_statusFlags)")
    
    df = df.Define("gen_mHH", "GenHHVars.gen_mHH")
    df = df.Define("gen_CosThetaStar_HH", "GenHHVars.gen_CosThetaStar_HH")
    df = df.Define("gen_pT_HH", "GenHHVars.gen_pT_HH")
    
    # Get all column names to save
    all_columns = df.GetColumnNames()
    all_columns = [str(c) for c in all_columns]
    
    # Remove the temporary struct column
    if "GenHHVars" in all_columns:
        all_columns.remove("GenHHVars")
    
    print(f"Saving {len(all_columns)} branches to output file...")
    print("New branches: gen_mHH, gen_CosThetaStar_HH, gen_pT_HH")
    
    # Save to output file
    snapshot_opts = ROOT.RDF.RSnapshotOptions()
    snapshot_opts.fMode = "RECREATE"
    snapshot_opts.fCompressionAlgorithm = ROOT.ROOT.kLZ4
    snapshot_opts.fCompressionLevel = 4
    
    df.Snapshot(tree_name, output_file, all_columns, snapshot_opts)
    
    print(f"Successfully wrote output to: {output_file}")


def add_gen_variables_parquet(input_file, output_file):
    """Add gen HH variables to parquet file using pandas/uproot"""
    try:
        import uproot
        import awkward as ak
        import pandas as pd
    except ImportError:
        print("ERROR: Need uproot, awkward, and pandas for parquet processing")
        print("Install with: pip install uproot awkward pandas pyarrow")
        sys.exit(1)
    
    # Read the parquet file
    print(f"Reading {input_file}...")
    df = pd.read_parquet(input_file)
    
    # Check if we have GenPart arrays (may need to convert from ROOT first)
    if 'GenPart_pt' not in df.columns:
        print("ERROR: GenPart branches not found in parquet file!")
        print("You may need to convert from ROOT format first using uproot/awkward")
        sys.exit(1)
    
    print("Calculating gen-level HH variables...")
    
    # Extract GenPart arrays
    n_events = len(df)
    gen_mHH = np.zeros(n_events, dtype=np.float32)
    gen_CosThetaStar_HH = np.zeros(n_events, dtype=np.float32)
    gen_pT_HH = np.zeros(n_events, dtype=np.float32)
    
    # Process each event
    for i in range(n_events):
        if i % 10000 == 0:
            print(f"  Processing event {i}/{n_events}...")
        
        # Get GenPart info for this event
        pt = np.array(df['GenPart_pt'].iloc[i])
        eta = np.array(df['GenPart_eta'].iloc[i])
        phi = np.array(df['GenPart_phi'].iloc[i])
        mass = np.array(df['GenPart_mass'].iloc[i])
        pdgId = np.array(df['GenPart_pdgId'].iloc[i])
        statusFlags = np.array(df['GenPart_statusFlags'].iloc[i])
        
        # Find Higgs bosons (pdgId = 25, isLastCopy flag)
        higgs_mask = (np.abs(pdgId) == 25) & ((statusFlags & (1 << 13)) != 0)
        higgs_indices = np.where(higgs_mask)[0]
        
        if len(higgs_indices) < 2:
            continue  # Skip events without two Higgs bosons
        
        # Get the two Higgs 4-momenta
        idx1, idx2 = higgs_indices[0], higgs_indices[1]
        
        # Convert to Cartesian coordinates
        px1 = pt[idx1] * np.cos(phi[idx1])
        py1 = pt[idx1] * np.sin(phi[idx1])
        pz1 = pt[idx1] * np.sinh(eta[idx1])
        E1 = np.sqrt(px1**2 + py1**2 + pz1**2 + mass[idx1]**2)
        
        px2 = pt[idx2] * np.cos(phi[idx2])
        py2 = pt[idx2] * np.sin(phi[idx2])
        pz2 = pt[idx2] * np.sinh(eta[idx2])
        E2 = np.sqrt(px2**2 + py2**2 + pz2**2 + mass[idx2]**2)
        
        # HH system
        px_HH = px1 + px2
        py_HH = py1 + py2
        pz_HH = pz1 + pz2
        E_HH = E1 + E2
        
        # Calculate mHH and pT_HH
        gen_mHH[i] = np.sqrt(E_HH**2 - px_HH**2 - py_HH**2 - pz_HH**2)
        gen_pT_HH[i] = np.sqrt(px_HH**2 + py_HH**2)
        
        # Calculate CosThetaStar (angle in HH rest frame)
        # Boost H1 to HH rest frame
        beta_x = px_HH / E_HH
        beta_y = py_HH / E_HH
        beta_z = pz_HH / E_HH
        gamma = E_HH / gen_mHH[i]
        
        # Boost transformation
        beta_dot_p1 = beta_x * px1 + beta_y * py1 + beta_z * pz1
        gamma_factor = (gamma - 1.0) / (beta_x**2 + beta_y**2 + beta_z**2) if (beta_x**2 + beta_y**2 + beta_z**2) > 0 else 0.0
        
        pz1_boosted = pz1 - beta_z * (gamma * E1 - gamma_factor * beta_dot_p1)
        p1_boosted_mag = np.sqrt(
            (px1 - beta_x * (gamma * E1 - gamma_factor * beta_dot_p1))**2 +
            (py1 - beta_y * (gamma * E1 - gamma_factor * beta_dot_p1))**2 +
            pz1_boosted**2
        )
        
        if p1_boosted_mag > 0:
            gen_CosThetaStar_HH[i] = pz1_boosted / p1_boosted_mag
    
    # Add new columns to dataframe
    df['gen_mHH'] = gen_mHH
    df['gen_CosThetaStar_HH'] = gen_CosThetaStar_HH
    df['gen_pT_HH'] = gen_pT_HH
    
    print(f"Saving to {output_file}...")
    df.to_parquet(output_file, compression='snappy')
    
    print("Successfully added gen-level HH variables!")
    print(f"Output saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Add generator-level HH variables for EFT reweighting"
    )
    parser.add_argument('-i', '--input', required=True, help='Input file (ROOT or parquet)')
    parser.add_argument('-o', '--output', required=True, help='Output file')
    parser.add_argument('-t', '--tree', default='Events', help='Tree name (for ROOT files)')
    parser.add_argument('-f', '--format', choices=['root', 'parquet'], default='root',
                       help='File format (default: root)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("Adding generator-level HH variables for EFT reweighting")
    print("="*80)
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print(f"Format: {args.format}")
    print()
    
    if args.format == 'root':
        add_gen_variables_root(args.input, args.output, args.tree)
    else:
        add_gen_variables_parquet(args.input, args.output)
    
    print()
    print("="*80)
    print("DONE!")
    print("="*80)


if __name__ == "__main__":
    main()

