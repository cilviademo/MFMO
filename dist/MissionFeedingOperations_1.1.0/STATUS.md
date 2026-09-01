# READY FOR PATH A ASSEMBLY

Not yet a validated final release. It becomes DEV/PILOT RELEASE CANDIDATE only
after the platform cycle completes on the .mil side:

  import Artifact1 → blank wrapper app + 19 sources → bump version to 1.1.0 →
  export → scripts/assemble_full_solution.sh → import candidate → open once in
  Studio (zero errors, Accessibility Checker) → publish → re-export →
  scripts/validate_final_export.sh <re-export>.zip

Then place beside this file:
  MissionFeedingOperations_1.1.0_UNMANAGED.zip
  MissionFeedingOperations_1.1.0_MANAGED.zip
  SHA256SUMS.txt   (sha256sum of both, plus Artifact1)

The Canvas/*.msapp here is REFERENCE / BUILD VALIDATION ONLY -- it carries no
platform-minted identity and is not a deployment artifact.
