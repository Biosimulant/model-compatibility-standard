# CT Volume — `imaging/ct-volume@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D8, D10, D11.

## Proposed scientific meaning

A three-dimensional X-ray computed tomography image: a voxel grid whose values are X-ray
attenuation in Hounsfield units, with declared voxel spacing, slice thickness and patient
orientation.

The name is a trap. "CT volume" means an image volume, not a measured volume of anything, and the
current profile declares its voxel values in millilitres — the unit of the quantity the name
accidentally suggests. Whichever meaning the reviewer confirms, the two must not share one profile.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3), and the place to state image-volume rather than measured-volume. |
| `representation.kind` | An array or artifact kind. |
| `dimensions.axes`, `axes[].name`, `axes[].meaning` | Three spatial axes. The current fixture declares two, which cannot index a voxel grid. |
| `dimensions.spatial_axes` | Which axes are spatial, and in what order. |
| `dimensions.pixel_spacing` | In-plane voxel size. Without it, voxel indices carry no physical scale and no measurement derived from the image is comparable. |
| `dimensions.slice_thickness` | The third dimension of the voxel. |
| `dimensions.orientation` | Patient orientation. Left-right flips are silent, clinically serious, and a known failure mode between DICOM (LPS) and NIfTI (RAS) conventions. |
| `dimensions.origin` | Anchors the grid in patient space. |
| `measurement.quantity` | X-ray attenuation, so the unit below is bound to something. |
| `measurement.unit` | `[hnsf'U]`, a real UCUM code for Hounsfield units. Not `mL`. |
| `measurement.scale` | `interval`: Hounsfield units are defined relative to water at 0 and air at -1000, so ratios are meaningless. |
| `biological_context.species` | Veterinary and preclinical CT share the modality but not the interpretation. |

**Conditional**

| Field | Condition |
|---|---|
| `artifact.format`, `artifact.format_version`, `artifact.sha256` | Required when exchanged as a file (DICOM, NIfTI), because the format carries the geometry and the orientation convention. Not required for an in-memory array. |
| `representation.precision` | Required when the consumer depends on stored bit depth and the rescale slope and intercept. |
| `origin.instrument_model`, `origin.protocol_ref` | Required when the port's use depends on acquisition (kVp, reconstruction kernel, contrast phase), which changes attenuation values materially. |
| `origin.processing_pipeline_ref`, `origin.registration_ref` | Required when the volume is resampled or registered to an atlas. |
| `security.deidentification` | Required for human subject data: CT volumes can be face-reconstructed, so de-identification level is a real gate. |
| `uncertainty.segmentation_confidence` | Required only for derived label or probability maps, which are separate profiles. |

**Recommended.** `biological_context.disease`; `biological_context.age` and `sex`;
`origin.observed_at`.

**Deliberately not gating.** `measurement.reference_range`. `artifact.compression` — lossless
compression does not change voxel values; lossy compression does, and belongs in the transformation
path rather than as a gate.

**Proposed new items.** A rescale declaration (slope and intercept) if Hounsfield conversion is to
be auditable; today only the stored values and the format convention imply it.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.unit` | equal within quantity kind | unknown | `[hnsf'U]` vs arbitrary intensity INCOMPATIBLE |
| `dimensions.pixel_spacing`, `slice_thickness` | equal, or declared resampling | unknown | Different spacing is a resampling transformation, lossy in general |
| `dimensions.orientation` | equal, or declared exact reorientation | unknown | LPS to RAS is a lossless, defined transformation; an undeclared flip is a safety issue |
| `dimensions.axes` count | equal | unknown | A two-axis declaration cannot satisfy a three-axis consumer |

## What v0.1 gets wrong here

- Voxel values are declared in `mL` on a `ratio` scale: the wrong unit and the wrong scale for
  attenuation, and the unit of a different quantity entirely.
- Two axes for a 3-D volume (`[x, y]`), from the same name-substring rule that gives stroke volume
  spatial axes.
- The conversion fixture asserts `nM -> uM` (BMCS-SCI-011).
- No spacing, thickness or orientation is required, so any derived measurement is uncomparable.

## Fixtures to regenerate

- **positive**: three spatial axes with spacing and thickness, orientation declared, unit
  `[hnsf'U]`, `scale: interval`, species `NCBITaxon:9606`, artifact format DICOM with digest.
- **lossless**: LPS to RAS reorientation.
- **lossy**: resampling to different voxel spacing — approval required.
- **contradiction**: `[hnsf'U]` vs `mL`; two-axis vs three-axis; different orientation with no
  declared transform.
- **unknown**: spacing absent; orientation absent.

## Questions for the reviewer

1. Is this profile an image volume, a measured anatomical volume, or both under one name? If both,
   it must be split before review.
2. Should the orientation convention be a declared enumeration (LPS, RAS) or inherited from the
   artifact format?
3. Must contrast phase be required rather than conditional for clinical use?
4. Should dose and reconstruction kernel gate compatibility for quantitative CT (for example bone
   densitometry), where they change the numbers?
5. Is `[hnsf'U]` acceptable to implementers, or should the profile carry a plain enumeration?

## Sources to pin

`dicom-ps3.3` (image geometry, orientation, rescale); the NIfTI-1 specification (for the RAS
convention); `ucum-2.2` (`[hnsf'U]` confirmed present); `stevens-1946` (interval scale);
`boellaard-2015-suv` is the PET analogue and should be cited in that profile rather than here. Each
needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011, BMCS-SCI-013 (the axis and unit defects appear in the register rather than as
dedicated cases); add an axis-count invariant in Phase 1.
