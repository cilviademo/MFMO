# READY FOR PATH A ASSEMBLY

Not yet a validated final release. It becomes DEV/PILOT RELEASE CANDIDATE only
after the platform cycle completes on the .mil side:

  import Artifact1 → blank wrapper app + 19 sources → bump version to 1.1.0 →
  export → scripts/assemble_full_solution.sh → import candidate → open once in
  Studio (zero errors, delegation review, Accessibility Checker, Live Monitor
  smoke run) → publish → re-export → scripts/validate_final_export.sh
  <re-export>.zip → pac solution check against the DoD checker endpoint.

This bundle is SELF-CONTAINED: the assembler's canvas source, every Python
module its validators import, the full provisioning package, and the docs the
checklists cite all travel inside it. SHA256SUMS.txt is the integrity
manifest for every file here -- verify it before anything else:

  cd into this directory && sha256sum -c SHA256SUMS.txt

After the Studio cycle, place beside this file and append hashes:
  MissionFeedingOperations_1.1.0_UNMANAGED.zip
  MissionFeedingOperations_1.1.0_MANAGED.zip

The Canvas/*.msapp here is REFERENCE / BUILD VALIDATION ONLY -- it carries no
platform-minted identity and is not a deployment artifact.
