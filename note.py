jsonPath = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/BTV/{}/btagging.json.gz"
    Python 3.11.9 (main, Jun 24 2024, 14:32:54) [GCC 11.3.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import correctionlib
    >>> btaggingJsonFile= 'btagging.json'
    >>> CSet=correctionlib.CorrectionSet.from_file(btaggingJsonFile)
    >>> for key in CSet.keys():
    ...     print(key)
    ... 
    deepJet_comb
    deepJet_light
    deepJet_mujets
    deepJet_shape
    deepJet_wp_values
    particleNet_comb
    particleNet_light
    particleNet_mujets
    particleNet_shape
    particleNet_wp_values
    robustParticleTransformer_comb
    robustParticleTransformer_light
    robustParticleTransformer_mujets
    robustParticleTransformer_shape
    robustParticleTransformer_wp_values

    >>> deepJetWpValues=CSet["deepJet_wp_values"]
    >>> for input in deepJetWpValues.inputs:

    ...     print(input.name)
    ... 
    working_point
    >>> deepJetWpValues.evaluate("M")
    0.3196
   
    >>> pNetWpValues=CSet["particleNet_wp_values"]
    >>> for input in pNetWpValues.inputs:
    ...     print(input.name)
    ... 
    working_point
    >>> pNetWpValues.evaluate("L")
    0.0499