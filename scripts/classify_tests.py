#!/usr/bin/env python3
"""Classify every test in the suite by what its passing actually proves.

A suite written against the generator that produced the artifact can pass in
full while the tests and the generator share one wrong premise. Counting tests
does not distinguish those cases; this does.

  BEHAVIOURAL  Exercises logic against data or an external standard. Something
               is computed and compared to an answer that did not come out of
               the code under test.
  STRUCTURAL   Asserts that two things this repository generates agree. Real
               value -- it catches drift -- but it cannot tell you the shared
               premise is right.
  POLICY       Asserts a settled decision. These are the dangerous ones: a
               policy test outlives the decision it encodes, and then it fails
               the correct configuration and argues for the rejected one.

Classification is DECLARED here, per test class, not inferred. An unclassified
class fails this script, so a new test class cannot slip in unlabelled.

  python3 scripts/classify_tests.py           counts and the table
  python3 scripts/classify_tests.py --policy  list every POLICY test by name
"""
import ast
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS = os.path.join(ROOT, "tests")

B, S, P = "BEHAVIOURAL", "STRUCTURAL", "POLICY"

# module -> class -> (kind, one-line justification)
CLASSIFICATION = {
    "test_status_engine": {
        "TestFixtureCases":         (B, "the engine run against fixture cases with hand-written expected states"),
        "TestNonNegotiables":       (B, "each of the twelve rules exercised on constructed inputs"),
        "TestTransliterationsAgree":(B, "Python, Power Fx and Logic Apps evaluated against one fixture set"),
        "TestReconciliationHeld":   (P, "the ten reconciliation rulings stay applied"),
    },
    "test_folder_resolver": {
        "FiscalYear":            (B, "date arithmetic against known DAF fiscal-year boundaries"),
        "FiscalYearFolder":      (B, "folder matching against constructed listings"),
        "MonthFolder":           (B, "month-folder matching across the naming variants seen on the sites"),
        "Resolve":               (B, "end-to-end resolution against constructed listings"),
        "FailClosed":            (B, "each failure path exercised and its code checked"),
        "SeededDestinations":    (P, "the shape the destination seed ships in"),
        "Sanitising":            (B, "path sanitising against adversarial inputs"),
        "Versioning":            (B, "version suffixing against existing-file listings"),
        "SpecAgreesWithTheCode": (S, "the definition.md and the resolver say the same thing"),
        "BindingsAreDocumented": (S, "site-bindings.md covers what the schema declares"),
        "ThePathUsesTheUrlSegment": (B, "the built path is checked against the segment, not the display name"),
        "TheFallbackCeiling":    (B, "fallback refused at and above the library root, computed per row"),
    },
    "test_eom01": {
        "TestIdempotency":                    (B, "the generator run twice against the real registry"),
        "TestFacilityIdIsNullNotEmptyString": (B, "payload inspection across all three scopes"),
        "TestOnboardingGate":                 (B, "generation gated on the flag, run and counted"),
        "TestOperatingModelFollowsTheFacility":(B, "model filter applied at facility scope only, verified by run"),
        "TestCatalogueRespected":             (B, "frequency and scope filters exercised per period"),
        "TestGeneratedStatus":                (B, "the status engine run on generated rows"),
        "TheBackfillWindowIsEnforced":        (B, "periods inside and outside the window generated and counted"),
        "EverySixActiveRequirementIsFacilityScope": (P, "the programme's scope ruling stays applied"),
    },
    "test_design_tokens": {
        "SixStatesExist":                   (P, "the six-state palette is the settled model"),
        "EveryChipIsReadable":              (B, "WCAG contrast ratios computed from the token values"),
        "AmberIsNotYellow":                 (B, "ΔE2000 and hue separation computed between the two tokens"),
        "TheDocumentedRatiosAreTrue":       (B, "documented ratios recomputed from the tokens"),
        "ThePrototypeTeachesSixStates":     (S, "the prototype and the token file agree"),
        "ThePeriodSelectorIsGenerated":     (S, "the selector reads the generator, not a literal list"),
        "EveryInteractiveControlHasAName":  (S, "every control in the source declares a label"),
        "NothingTheAdminOwnsIsHardcoded":   (P, "the five admin-owned values stay in configuration"),
        "ColourIsNeverTheOnlyChannel":      (P, "accessibility ruling: text and icon accompany colour"),
        "NoCountIsReportedWithoutItsDenominator": (P, "the reporting ruling stays applied"),
        "TheCanvasSourceIsExtractable":     (B, "the extractor run over the real source, block scalars included"),
        "CanvasChecksAreWired":             (B, "both canvas audits executed, and proven to fail on a planted violation"),
        "TheApprovedScreenSetIsPresent":    (P, "the approved screen set, named"),
        "TheSourceIsRealYaml":              (B, "every source file run through a real YAML parser; ten had never passed one"),
        "TheMsappSourceIsFreshAndValid":    (B, "the generated dialect regenerated, schema-validated, and the validator proven non-vacuous"),
    },
    "test_flow_expression": {
        "TheInterpreterIsStrict":        (B, "the interpreter itself tested on cases with known answers"),
        "TheExpressionIsWellFormed":     (S, "the emitted expression parses and is shaped as expected"),
        "TheExpressionAgreesWithTheEngine": (B, "the expression evaluated against the engine's fixture set"),
    },
    "test_hardening": {
        "SplittingFilters":                   (B, "delegable filter splitting exercised on queries"),
        "TheGuard":                           (B, "the schema guard run against matching and mismatched versions"),
        "TheGuardCatchesTheDefectThatCostAMonth": (B, "the historical defect reproduced and caught"),
        "EmptyFilterMeansNoConstraint":       (B, "empty-filter semantics exercised"),
        "RequiredArtifactsMustSaySomething":  (B, "the emptiness check run against planted stubs"),
        "InlineExceptionsMustBeExplained":    (B, "marker parsing run against good and bad markers"),
        "TheScanStillPasses":                 (B, "each rule fired on a planted specimen and held off a lookalike"),
        "ConnectorsMatchTheAllowlist":        (P, "the connector allowlist is the settled policy"),
    },
    "test_flow_bodies": {
        "TheGraphIsSound":                   (B, "runAfter graph walked for cycles and unreachable actions"),
        "NothingEnvironmentSpecificIsHardCoded": (S, "generated JSON checked for literals"),
        "ConnectorsAreOnTheAllowlist":       (P, "the connector allowlist is the settled policy"),
        "EveryWriteLoopIsSerial":            (S, "every foreach in the generated JSON pins concurrency"),
        "TheSpecificationInvariantsHold":    (S, "each body contains the actions its spec describes"),
        "EveryFlowImportsDisabled":          (P, "flows ship Draft by decision"),
    },
    "test_package": {
        "TheFilesAreWellFormed":            (S, "the emitted XML and JSON parse"),
        "TheManifestIsComplete":            (S, "solution components and configuration agree"),
        "NoOrphanedReference":              (S, "every reference resolves within the package"),
        "ThePackageHasNoCanvasApp":         (P, "no .msapp and no fabricated Canvas component"),
        "TheFlowsAreWiredEvenWhereTheyAreUnfinished": (S, "each workflow is registered and parameterised"),
        "NothingEnvironmentSpecificIsBaked":(P, "no connection or environment variable values in the package"),
        "VersionsAgree":                    (S, "one version across solution, config and changelog"),
        "CustomizationsMatchesTheConfiguration": (S, "Customizations.xml and the config files agree"),
        "TheDependencyManifestIsUsable":    (S, "the manifest covers what the package needs"),
        "LegacyIntakeShipsUnbound":         (P, "EOM-02b ships as an unbound template"),
        "ImportChecklistIsSequenced":       (P, "the import order and its gates are settled"),
        "TheAssemblyRunbookIsCurrent":      (S, "the runbook's counts and the solution agree"),
        "TheExportValidatorWorks":          (B, "the export validator run against five fixtures, four of them broken"),
        "ReleaseNotesDistinguishTheTwoArtifacts": (P, "the two artifacts have different provenance and say so"),
        "KnownLimitationsNamesWhatIsOpen":  (P, "the two open items stay named and NOT TESTABLE stays listed"),
        "ThePilotOrderIsComplete":          (P, "the pilot sequence, with notifications last"),
    },
    "test_schema": {
        "TestSchemaItself":          (B, "schema invariants computed: nullability, index cap, key shape"),
        "TestRequirementSeed":       (P, "the requirement catalogue is the settled configuration"),
        "TestConfigurationSeeds":    (P, "the seeded configuration is the settled configuration"),
        "TestNoHardCodedEnvironment":(P, "no environment literal in source"),
        "TestFlowSpecs":             (S, "flow specs and schema agree"),
        "TestAppSource":             (S, "app source and schema agree"),
        "ProvisioningIsVerifiable":  (B, "the verifier run against a complete and a broken tenant fixture"),
    },
    "test_schema_manifest": {
        "ListsReferencedExist":            (S, "every list named anywhere exists in the schema"),
        "ColumnsReferencedExist":          (S, "every column named anywhere exists in the schema"),
        "InternalNamesAreSafe":            (B, "internal-name encoding computed from display names"),
        "TheManifestIsCurrent":            (S, "the manifest and the schema agree"),
        "SchemaVersionIsGated":            (S, "every flow and the app compare the same version"),
        "SubmissionIsRequestIdempotent":   (P, "request idempotency is the settled design"),
        "OneCurrentSubmissionPerItem":     (P, "one current submission per item is the settled design"),
        "ReportIndexTableMatchesTheSchema":(S, "the report's table and the schema agree"),
        "NoDocumentStatesAStaleTotal":     (S, "every stated total and the schema agree"),
        "EveryTestIsClassified":           (S, "every test class carries a declared kind"),
    },
    "test_duplication": {
        "ApplicabilityAgrees":               (B, "the Power Fx and Python predicates evaluated on the same cases"),
        "TheFxStillHasTheShapeTheModelAssumes": (S, "the Fx source matches what the comparison assumes"),
        "OneImplementationPerConcept":       (P, "one reference implementation per concept"),
        "TheSecondUploadArchitectureIsGone": (P, "the central evidence library stays removed"),
    },
}


def walk():
    for fn in sorted(os.listdir(TESTS)):
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        mod = fn[:-3]
        tree = ast.parse(open(os.path.join(TESTS, fn), encoding="utf-8").read())
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            methods = [x.name for x in node.body
                       if isinstance(x, ast.FunctionDef) and x.name.startswith("test")]
            if methods:
                yield mod, node.name, methods


def main():
    counts = {B: 0, S: 0, P: 0}
    rows, unclassified, policy = [], [], []
    for mod, cls, methods in walk():
        entry = CLASSIFICATION.get(mod, {}).get(cls)
        if entry is None:
            unclassified.append(f"{mod}.{cls}")
            continue
        kind, why = entry
        counts[kind] += len(methods)
        rows.append((mod, cls, kind, len(methods), why))
        if kind == P:
            policy.extend(f"{mod}.{cls}.{m}" for m in methods)

    if unclassified:
        print("UNCLASSIFIED TEST CLASSES — classify them in this file:")
        for u in unclassified:
            print(f"  {u}")
        return 1

    if "--policy" in sys.argv:
        print(f"POLICY tests ({len(policy)}):")
        for p in policy:
            print(f"  {p}")
        return 0

    total = sum(counts.values())
    print("| Module | Class | Kind | Tests | What a pass means |")
    print("|---|---|---|---:|---|")
    for mod, cls, kind, n, why in rows:
        print(f"| `{mod}` | `{cls}` | **{kind[0]}** | {n} | {why} |")
    print()
    for kind in (B, S, P):
        print(f"{kind:<12} {counts[kind]:>4}   {counts[kind]*100//total}%")
    print(f"{'TOTAL':<12} {total:>4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
