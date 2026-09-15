# Wave C — cell, immunology, microbiology, virology, developmental, ecology, evolution

175 profiles. 3 in the pilot. See the [shared brief](README.md) for what every reviewer is asked to
do and what approval means.

## Who is needed

- An **immunologist** for assay-defined quantities: dilution titres, international standards,
  isotypes, and why two ELISAs do not agree.
- A **microbial ecologist or microbiome analyst** for community data: taxonomy releases, ranks,
  relative versus absolute abundance, and compositional constraints.
- A **virologist** for infectivity: plaque assays, TCID50, host cell dependence, and the gap
  between genome copies and infectious units.
- A **cell biologist** for culture-derived measurements: rates, viability, and how culture
  conditions change the number.
- An **evolutionary biologist or population ecologist** for rates and distances: per-generation
  bases, substitution models, and population-level denominators.

This wave has the widest spread of expertise and probably needs the most reviewers.

## Pilot profiles

| Profile | The question it tests |
|---|---|
| [immunology/antibody-titer](../pilot-profiles/immunology--antibody-titer.md) | Assay-defined units and calibration to an international standard |
| [microbiology/taxonomic-abundance](../pilot-profiles/microbiology--taxonomic-abundance.md) | Many organisms in one port, and a taxonomy that changes between releases |
| [virology/infectious-titer](../pilot-profiles/virology--infectious-titer.md) | Host and pathogen as separate declarations; units defined by an assay |

## Questions this wave settles for everyone else

1. **How does a port describe more than one organism?** A single species field cannot express a
   host and a pathogen, or a community. This is decision D5, and this wave is where it bites.
2. **What does an assay-defined unit mean for compatibility?** A titre is a property of a
   virus-cell-protocol combination. Should the assay be part of the quantity, or context around it?
3. **When may a conventional conversion factor be applied?** TCID50 to PFU has a familiar factor
   that is a Poisson approximation. Is that an inference requiring approval, or never allowed?
4. **How are compositional data handled?** Relative abundances sum to one, which makes them a
   different statistical object from counts.

## Known defects in this wave's profiles

- Every positive fixture in these domains declares `NCBITaxon:9606`, so a microbial community
  vector, a viral titre and an ecological abundance are all labelled human.
- Infectious titre is dimensionless, with no volume basis and no assay.
- Taxonomic abundance requires one species for a community, with no taxonomy release and no rank.
- Antibody titre declares a ratio scale for a two-fold dilution series.
- Cell migration rate is declared in `1/s` on a probability scale, when the quantity is usually a
  speed.
- Attack rate is declared in `1/s`, though it is a proportion.
- Mutation and recombination rates are declared in `1/s`, with no per-site or per-generation basis.
