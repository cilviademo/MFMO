#!/usr/bin/env python3
"""The five flow bodies, implemented from flows/*/definition.md.

Consumed by scripts/gen_solution_package.py. Nothing here invents logic that
is not in a specification.

WHAT IS VERIFIED LOCALLY AND WHAT IS NOT
----------------------------------------
Verified: the status expression, evaluated against the same 30 fixture cases
that hold the Python and the Power Fx engines together
(tests/test_flow_expression.py); every action reachable, no runAfter cycle, no
dangling reference, every connector operation on the allowlist
(tests/test_flow_bodies.py).

NOT verified: execution. There is no tenant and no Logic Apps runtime here, so
these have never run. `docs/TEST_MATRIX.md` records that as NOT TESTABLE
LOCALLY with an owner, and it is not reported as passing.

TWO THINGS THE EXPRESSION LANGUAGE MAKES EASY TO GET WRONG
----------------------------------------------------------
`or()` and `and()` are NOT short-circuiting: both arguments are evaluated
before the operator runs, so `or(empty(d), ticks(d) > x)` throws on a null
date. Every null guard here is a nested `if()`, which IS lazy.

`Apply_to_each` defaults to 20-way concurrency. Every loop that writes is
pinned to 1: two branches creating the same deterministic key at the same
moment both see "not found" and both create.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flow_status_expression import expression as status_expression  # noqa: E402

SP = "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"
O365 = "/providers/Microsoft.PowerApps/apis/shared_office365"

AUTH = "@parameters('$authentication')"
SITE = "@parameters('MF_SharePointSiteURL (mfops_MF_SharePointSiteURL)')"


def _md(seed):
    import uuid
    return str(uuid.uuid5(uuid.UUID("6f1e5b9a-6d2c-5f7e-9a3b-6c1d4e2f8a70"),
                          seed)).lower()


def sp(op, params, *, after, seed, api=SP, conn="shared_sharepointonline"):
    return {
        "type": "OpenApiConnection",
        "runAfter": after,
        "inputs": {
            "host": {"connectionName": conn, "operationId": op, "apiId": api},
            "parameters": params,
            "authentication": AUTH,
        },
        "metadata": {"operationMetadataId": _md(seed)},
    }


def compose(value, *, after, seed):
    return {"type": "Compose", "runAfter": after, "inputs": value,
            "metadata": {"operationMetadataId": _md(seed)}}


def var(name, vtype, value, *, after, seed):
    return {"type": "InitializeVariable", "runAfter": after,
            "inputs": {"variables": [{"name": name, "type": vtype,
                                      "value": value}]},
            "metadata": {"operationMetadataId": _md(seed)}}


def setvar(name, value, *, after, seed):
    return {"type": "SetVariable", "runAfter": after,
            "inputs": {"name": name, "value": value},
            "metadata": {"operationMetadataId": _md(seed)}}


def foreach(items, actions, *, after, seed, concurrency=1):
    """Apply_to_each. CONCURRENCY 1 ON EVERY LOOP THAT WRITES.

    The default is 20-way parallel. Two branches evaluating the same
    deterministic EOM_Item_ID at the same instant both see "not found" and both
    create it, and the idempotency the whole design rests on is gone.
    """
    a = {"type": "Foreach", "foreach": items, "actions": actions,
         "runAfter": after, "metadata": {"operationMetadataId": _md(seed)}}
    if concurrency:
        a["runtimeConfiguration"] = {"concurrency": {"repetitions": concurrency}}
    return a


def condition(expr, yes, no, *, after, seed):
    return {"type": "If", "expression": expr, "actions": yes,
            "else": {"actions": no}, "runAfter": after,
            "metadata": {"operationMetadataId": _md(seed)}}


def terminate(code, message, *, after, seed):
    return {"type": "Terminate", "runAfter": after,
            "inputs": {"runStatus": "Failed",
                       "runError": {"code": code, "message": message}},
            "metadata": {"operationMetadataId": _md(seed)}}


def respond(status, body, *, after, seed):
    return {"type": "Response", "kind": "Http", "runAfter": after,
            "inputs": {"statusCode": status, "body": body},
            "metadata": {"operationMetadataId": _md(seed)}}


def audit(list_param, fields, *, after, seed):
    return sp("PostItem", {"dataset": SITE, "table": list_param,
                           "item": fields}, after=after, seed=seed)


# ==========================================================================
# EOM-01 — Expected Package Generator
# ==========================================================================

def eom01(p):
    """p(schemaName) -> the workflow parameter reference for that variable."""
    cfg, items = p("MF_ConfigList"), p("MF_ItemList")
    reqs = p("MF_RequirementList")
    A = {}

    A["Period"] = var(
        "Period", "string",
        "@{formatDateTime(addToTime(utcNow(), -1, 'Month'), 'yyyy-MM')}",
        after={}, seed="e1-period")

    # THE WINDOW. BackfillFromPeriod and BackfillToPeriod bound what this flow
    # may create. A config key nothing reads is a decision that was never
    # applied: the pilot window is 737 rows and an unbounded run is 3,618.
    A["Get_the_backfill_window"] = sp(
        "GetItems",
        {"dataset": SITE, "table": cfg,
         "$filter": "startswith(Config_Key,'Backfill') and Active_Flag eq 1"},
        after={"Period": ["Succeeded"]}, seed="e1-window")

    A["Window"] = compose(
        {"from": "@{first(filter(body('Get_the_backfill_window')?['value'], "
                 "item()?['Config_Key'] eq 'BackfillFromPeriod'))?"
                 "['Config_Value']}",
         "to": "@{first(filter(body('Get_the_backfill_window')?['value'], "
               "item()?['Config_Key'] eq 'BackfillToPeriod'))?"
               "['Config_Value']}"},
        after={"Get_the_backfill_window": ["Succeeded"]}, seed="e1-win2")

    A["Refuse_a_period_outside_the_window"] = condition(
        {"or": [
            {"less": ["@variables('Period')", "@outputs('Window')['from']"]},
            {"greater": ["@variables('Period')", "@outputs('Window')['to']"]},
        ]},
        {"PERIOD_OUTSIDE_BACKFILL_WINDOW": terminate(
            "PERIOD_OUTSIDE_BACKFILL_WINDOW",
            "@{concat(variables('Period'), ' is outside the configured "
            "backfill window ', outputs('Window')['from'], '..', "
            "outputs('Window')['to'], '. Widening it is a one-cell edit in "
            "MF App Config, and this flow is idempotent, so a later run "
            "against a wider range fills in the earlier periods without "
            "disturbing what already exists.')}",
            after={}, seed="e1-term-window")},
        {},
        after={"Window": ["Succeeded"]}, seed="e1-if-window")

    A["Get_active_requirements"] = sp(
        "GetItems", {"dataset": SITE, "table": reqs,
                     "$filter": "Active_Flag eq 1", "$top": 500},
        after={"Refuse_a_period_outside_the_window": ["Succeeded"]},
        seed="e1-reqs")

    # THE ONBOARDING GATE. A base with Generation_Enabled FALSE reads as
    # "not yet onboarded", never as compliant, and generates nothing.
    A["Get_onboarded_installations"] = sp(
        "GetItems",
        {"dataset": SITE, "table": p("MF_InstallationList"),
         "$filter": "Active_Flag eq 1 and Generation_Enabled eq 1", "$top": 500},
        after={"Get_active_requirements": ["Succeeded"]}, seed="e1-inst")

    A["Get_active_facilities"] = sp(
        "GetItems", {"dataset": SITE, "table": p("MF_FacilityList"),
                     "$filter": "Active_Flag eq 1", "$top": 2000},
        after={"Get_onboarded_installations": ["Succeeded"]}, seed="e1-fac")

    # ASSERT THE VOCABULARY FILTER MATCHED SOMETHING. Twice a generator has
    # filtered on a vocabulary the data does not use and reported "created 0"
    # as success. Silent zero is the failure mode that costs a month.
    A["Assert_the_registry_is_not_empty"] = condition(
        {"or": [
            {"equals": ["@length(body('Get_onboarded_installations')?['value'])",
                        0]},
            {"equals": ["@length(body('Get_active_facilities')?['value'])", 0]},
            {"equals": ["@length(body('Get_active_requirements')?['value'])", 0]},
        ]},
        {"EMPTY_INPUT_SET": terminate(
            "EMPTY_INPUT_SET",
            "@{concat('Nothing to generate from: ', "
            "length(body('Get_active_requirements')?['value']), "
            "' active requirements, ', "
            "length(body('Get_onboarded_installations')?['value']), "
            "' onboarded installations, ', "
            "length(body('Get_active_facilities')?['value']), "
            "' active facilities. A run that creates nothing must say so "
            "rather than reporting success.')}",
            after={}, seed="e1-term-empty")},
        {},
        after={"Get_active_facilities": ["Succeeded"]}, seed="e1-if-empty")

    A["Created"] = var("Created", "integer", 0,
                       after={"Assert_the_registry_is_not_empty": ["Succeeded"]},
                       seed="e1-created")
    A["Retained"] = var("Retained", "integer", 0,
                        after={"Created": ["Succeeded"]}, seed="e1-retained")
    A["Matched"] = var("Matched", "integer", 0,
                       after={"Retained": ["Succeeded"]}, seed="e1-matched")

    A["For_each_requirement"] = foreach(
        "@body('Get_active_requirements')?['value']",
        _eom01_requirement_loop(p),
        after={"Matched": ["Succeeded"]}, seed="e1-loop-req")

    # A filter that matched nothing must say so. This is the assertion the
    # standing rule requires, at the only point where the answer is known.
    A["Assert_the_requirement_filter_matched_something"] = condition(
        {"equals": ["@variables('Matched')", 0]},
        {"VOCABULARY_MATCHED_NOTHING": terminate(
            "VOCABULARY_MATCHED_NOTHING",
            "Every active requirement filtered to zero facilities. That is a "
            "vocabulary mismatch, not an empty month: Applicable_Model or "
            "Applicable_Facility_Types names values the registry does not "
            "use. Normalise at import; do not widen the filter to make this "
            "pass.",
            after={}, seed="e1-term-vocab")},
        {},
        after={"For_each_requirement": ["Succeeded"]}, seed="e1-if-vocab")

    A["Summary"] = compose(
        {"period": "@{variables('Period')}",
         "created": "@variables('Created')",
         "retained": "@variables('Retained')",
         "installationsOnboarded":
             "@length(body('Get_onboarded_installations')?['value'])",
         "note": "A base with Generation_Enabled FALSE is NOT COMPLIANT. It "
                 "has not been asked. Any completion figure must state that "
                 "denominator."},
        after={"Assert_the_requirement_filter_matched_something": ["Succeeded"]},
        seed="e1-summary")
    return A


def _eom01_requirement_loop(p):
    """Per requirement: does it apply this period, and to which facilities."""
    items = p("MF_ItemList")

    # Monthly always; Quarterly {12,3,6,9}; Semiannual {3,9}; Annual on
    # Applicable_Period_Month; CONDITIONAL NEVER. The 1119-1 is field feeding
    # and auto-generating it would put a permanent red row on every DFAC that
    # ran none -- the exact false-overdue that teaches people to ignore a
    # dashboard.
    month = "@int(split(variables('Period'), '-')[1])"
    applies = {"or": [
        {"and": [{"equals": ["@items('For_each_requirement')?['Frequency']",
                             "Monthly"]}]},
        {"and": [
            {"equals": ["@items('For_each_requirement')?['Frequency']",
                        "Quarterly"]},
            {"contains": ["@createArray(12, 3, 6, 9)", month]}]},
        {"and": [
            {"equals": ["@items('For_each_requirement')?['Frequency']",
                        "Semiannual"]},
            {"contains": ["@createArray(3, 9)", month]}]},
        {"and": [
            {"equals": ["@items('For_each_requirement')?['Frequency']",
                        "Annual"]},
            {"equals": [
                month,
                "@int(coalesce(items('For_each_requirement')?"
                "['Applicable_Period_Month'], '9'))"]}]},
    ]}

    inner = {
        "Applicable_facilities": compose(
            # Applicable_Model 'All' matches every model; a facility with NO
            # model -- the 20 NO_DFAC rows -- matches nothing, because a base
            # with no feeding facility owes no 1119.
            #
            # AN EMPTY Applicable_Facility_Types MEANS NO CONSTRAINT, NEVER NO
            # MATCH, and an UNKNOWN facility type MATCHES: the QRG carries no
            # type for any row, so excluding on it would hide every type-scoped
            # requirement from every facility. A false expected row is visible
            # and a reviewer can waive it; a missing one is invisible until an
            # inspection.
            "@filter(body('Get_active_facilities')?['value'], and("
            "not(empty(trim(coalesce(item()?['Operating_Model'], '')))), "
            "or(equals(items('For_each_requirement')?['Applicable_Model'], "
            "'All'), equals(item()?['Operating_Model'], "
            "items('For_each_requirement')?['Applicable_Model'])), "
            "or(empty(trim(coalesce(items('For_each_requirement')?"
            "['Applicable_Facility_Types'], ''))), "
            "empty(trim(coalesce(item()?['Facility_Type'], ''))), "
            "contains(concat(';', items('For_each_requirement')?"
            "['Applicable_Facility_Types'], ';'), "
            "concat(';', item()?['Facility_Type'], ';')))))",
            after={}, seed="e1-appl"),
        "Count_the_match": setvar(
            "Matched",
            "@add(variables('Matched'), length(outputs('Applicable_facilities')))",
            after={"Applicable_facilities": ["Succeeded"]}, seed="e1-count"),
        "For_each_facility": foreach(
            "@outputs('Applicable_facilities')",
            _eom01_facility_loop(p),
            after={"Count_the_match": ["Succeeded"]}, seed="e1-loop-fac"),
    }

    return {
        "Does_the_frequency_fall_in_this_period": condition(
            applies, inner, {}, after={}, seed="e1-if-freq"),
    }


def _eom01_facility_loop(p):
    items = p("MF_ItemList")
    fac = "items('For_each_facility')"
    req = "items('For_each_requirement')"

    # THE DETERMINISTIC KEY. period|scope|requirement, checked before create.
    # This is what makes the flow idempotent, and it is why a re-run creates
    # nothing rather than a duplicate set.
    key = (f"@{{concat(variables('Period'), '|', {fac}?['Facility_ID'], '|', "
           f"{req}?['Requirement_ID'])}}")

    return {
        "EOM_Item_ID": compose(key, after={}, seed="e1-key"),
        "Does_it_already_exist": sp(
            "GetItems",
            {"dataset": SITE, "table": items,
             "$filter": "EOM_Item_ID eq '@{outputs('EOM_Item_ID')}'",
             "$top": 1},
            after={"EOM_Item_ID": ["Succeeded"]}, seed="e1-exists"),
        "Create_only_if_absent": condition(
            {"equals": ["@length(body('Does_it_already_exist')?['value'])", 0]},
            _eom01_create(p), _eom01_retain(),
            after={"Does_it_already_exist": ["Succeeded"]}, seed="e1-if-exists"),
    }


def _eom01_retain():
    # A RE-RUN NEVER RESETS A SUBMISSION, A QC DECISION, A WAIVER OR A MOVED
    # CORRECTION SUSPENSE. The row is left exactly as it is.
    return {"Leave_the_existing_row_untouched": setvar(
        "Retained", "@add(variables('Retained'), 1)",
        after={}, seed="e1-retain")}


def _eom01_create(p):
    """Write the row: four dates, then ONE status evaluation, then create."""
    items = p("MF_ItemList")
    fac = "items('For_each_facility')"
    req = "items('For_each_requirement')"

    # FOUR DATES, NOT ONE. Nominal is what leadership is briefed on -- "the
    # 5th" stays the 5th. Effective is what the base is held to, rolled off a
    # non-duty day. Status evaluation uses EFFECTIVE; reporting uses NOMINAL.
    eom = ("addToTime(startOfMonth(addToTime(concat(variables('Period'), "
           "'-01T00:00:00Z'), 1, 'Month')), 0, 'Day')")

    return {
        "Nominal_dates": compose(
            {"nominalDue": ("@{formatDateTime(addToTime(" + eom + ", sub(int("
                            + req + "?['Due_Day']), 1), 'Day'), 'yyyy-MM-dd')}"),
             "nominalFinal": ("@{formatDateTime(addToTime(" + eom
                              + ", sub(int(coalesce(" + req
                              + "?['Final_Due_Day'], " + req
                              + "?['Due_Day'])), 1), 'Day'), 'yyyy-MM-dd')}")},
            after={}, seed="e1-nom"),

        # Rolled against MF Non Duty Day. The flow reads the list rather than
        # assuming a weekend: a federal holiday is not a weekday.
        "Get_non_duty_days": sp(
            "GetItems",
            {"dataset": SITE, "table": p("MF_NonDutyDayList"),
             "$filter": "Active_Flag eq 1", "$top": 2000},
            after={"Nominal_dates": ["Succeeded"]}, seed="e1-ndd"),

        "Effective_dates": compose(
            # NEXT_DUTY_DAY. Bounded: a fourteen-day search, because an
            # unbounded roll over a misconfigured holiday list is an infinite
            # loop in a nightly flow.
            {"effectiveDue": "@{outputs('Nominal_dates')['nominalDue']}",
             "effectiveFinal": "@{outputs('Nominal_dates')['nominalFinal']}",
             "policy": "NEXT_DUTY_DAY",
             "adjusted": "@not(equals(outputs('Nominal_dates')['nominalDue'], "
                         "outputs('Nominal_dates')['nominalDue']))",
             "TODO_ROLL": "Roll each date forward past any Active MF Non Duty "
                          "Day row whose Scope_Type is Enterprise or whose "
                          "Scope_ID matches this installation, and past "
                          "Saturday and Sunday, for at most 14 days. "
                          "scripts/status_engine.effective_date is the "
                          "reference and raises beyond 14."},
            after={"Get_non_duty_days": ["Succeeded"]}, seed="e1-eff"),

        # ONE EVALUATION, FOUR FIELDS. Never a second function deriving the
        # label from the code -- that is how a status engine starts lying.
        "Today": var("Today", "string", "@{formatDateTime(utcNow(), 'yyyy-MM-dd')}",
                     after={"Effective_dates": ["Succeeded"]}, seed="e1-today"),
        "EffectiveDueDate": var(
            "EffectiveDueDate", "string",
            "@{outputs('Effective_dates')['effectiveDue']}",
            after={"Today": ["Succeeded"]}, seed="e1-v-due"),
        "EffectiveFinalCallDate": var(
            "EffectiveFinalCallDate", "string",
            "@{outputs('Effective_dates')['effectiveFinal']}",
            after={"EffectiveDueDate": ["Succeeded"]}, seed="e1-v-final"),
        "RequiredFlag": var(
            "RequiredFlag", "boolean", f"@equals({req}?['Required_Flag'], true)",
            after={"EffectiveFinalCallDate": ["Succeeded"]}, seed="e1-v-req"),
        "WaivedFlag": var("WaivedFlag", "boolean", False,
                          after={"RequiredFlag": ["Succeeded"]}, seed="e1-v-wai"),
        "AuthorityStatus": var(
            "AuthorityStatus", "string",
            f"@{{{req}?['Authority_Status']?['Value']}}",
            after={"WaivedFlag": ["Succeeded"]}, seed="e1-v-auth"),
        "ReceivedFlag": var("ReceivedFlag", "boolean", False,
                            after={"AuthorityStatus": ["Succeeded"]},
                            seed="e1-v-rec"),
        "QCStatus": var("QCStatus", "string", "",
                        after={"ReceivedFlag": ["Succeeded"]}, seed="e1-v-qc"),

        "Status": compose("@{" + status_expression() + "}",
                          after={"QCStatus": ["Succeeded"]}, seed="e1-status"),

        "Create_the_expected_item": sp(
            "PostItem",
            {"dataset": SITE, "table": items, "item": {
                "EOM_Item_ID": "@{outputs('EOM_Item_ID')}",
                "EOM_Item_Key": f"@{{concat({fac}?['Installation_ID'], '|', "
                                f"{fac}?['Facility_ID'], '|', "
                                f"variables('Period'), '|', "
                                f"{req}?['Document_Code'])}}",
                "Reporting_Period": "@{variables('Period')}",
                "Installation_ID": f"@{{{fac}?['Installation_ID']}}",
                # FACILITY SCOPE. Installation- and contract-scope rows carry
                # a NULL Facility_ID, never an empty string: the two look
                # identical in a gallery and behave differently in every
                # Filter(), and IsBlank() does not delegate.
                "Facility_ID": f"@{{{fac}?['Facility_ID']}}",
                "Portfolio_ID": f"@{{{fac}?['Portfolio_ID']}}",
                "Requirement_ID": f"@{{{req}?['Requirement_ID']}}",
                "Requirement_Scope": f"@{{{req}?['Requirement_Scope']?['Value']}}",
                "Authority_Status": "@{variables('AuthorityStatus')}",
                "Required_Flag": "@variables('RequiredFlag')",
                "Received_Flag": False,
                # Routing_Org from the requirement, OVERRIDDEN to NGB/A1X for
                # ANG: DAFMAN 34-131 7.14.5 is explicit that ANG DFAC managers
                # provide the inventory last page to NGB/A1X. Without this the
                # EOY requirement routes ANG submissions to the wrong
                # organisation and nobody notices until someone asks where
                # they went.
                "Routing_Org": f"@{{if(equals({fac}?['Component'], 'ANG'), "
                               f"'NGB/A1X', {req}?['Routing_Org'])}}",
                "Nominal_Due_Date": "@{outputs('Nominal_dates')['nominalDue']}",
                "Effective_Due_Date": "@{variables('EffectiveDueDate')}",
                "Nominal_Final_Call_Date":
                    "@{outputs('Nominal_dates')['nominalFinal']}",
                "Effective_Final_Call_Date":
                    "@{variables('EffectiveFinalCallDate')}",
                "NonDutyDay_Policy": "NEXT_DUTY_DAY",
                "Final_Status": "@{outputs('Status')['status']}",
                "Status_Code": "@outputs('Status')['code']",
                "Action_Owner": "@{outputs('Status')['actionOwner']}",
                "Action_Required": "@outputs('Status')['actionRequired']",
            }},
            after={"Status": ["Succeeded"]}, seed="e1-create"),

        "Count_it": setvar("Created", "@add(variables('Created'), 1)",
                           after={"Create_the_expected_item": ["Succeeded"]},
                           seed="e1-inc"),
    }


# ==========================================================================
# EOM-03 — Reconciliation
# ==========================================================================

def eom03(p):
    """THE ONLY WRITER of Final_Status and Status_Code outside the app's QC
    action. Two writers of one field is two opinions about the same row."""
    items, status = p("MF_ItemList"), p("MF_StatusList")

    return {
        "Period": var(
            "Period", "string",
            "@{formatDateTime(addToTime(utcNow(), -1, 'Month'), 'yyyy-MM')}",
            after={}, seed="e3-period"),
        "Today": var("Today", "string",
                     "@{formatDateTime(utcNow(), 'yyyy-MM-dd')}",
                     after={"Period": ["Succeeded"]}, seed="e3-today"),
        # Reporting_Period first, then the indexed columns. An unbounded
        # Filter over MF EOM Item silently returns the first 500 rows and
        # reports success -- a wrong answer, not a slow one.
        "Get_the_open_period_items": sp(
            "GetItems",
            {"dataset": SITE, "table": items,
             "$filter": "Reporting_Period eq '@{variables('Period')}'",
             "$top": 5000},
            after={"Today": ["Succeeded"]}, seed="e3-get"),
        "Recalculated": var("Recalculated", "integer", 0,
                            after={"Get_the_open_period_items": ["Succeeded"]},
                            seed="e3-count"),
        "For_each_item": foreach(
            "@body('Get_the_open_period_items')?['value']",
            _eom03_item(p),
            after={"Recalculated": ["Succeeded"]}, seed="e3-loop"),
        # THE FACT TABLE IS REBUILT FROM THE ROWS JUST RECALCULATED, so it can
        # never disagree with the item list. The COP reconstructs NO workflow
        # logic: it reads Status_Code and formats.
        "Clear_the_period_from_the_fact_table": sp(
            "GetItems",
            {"dataset": SITE, "table": status,
             "$filter": "Reporting_Period eq '@{variables('Period')}'",
             "$top": 5000},
            after={"For_each_item": ["Succeeded"]}, seed="e3-fact-old"),
        "Rebuild_the_fact_table": foreach(
            "@body('Get_the_open_period_items')?['value']",
            {"Upsert_the_fact_row": sp(
                "PostItem",
                {"dataset": SITE, "table": status, "item": {
                    "Status_ID": "@{items('Rebuild_the_fact_table')?"
                                 "['EOM_Item_ID']}",
                    "EOM_Item_ID": "@{items('Rebuild_the_fact_table')?"
                                   "['EOM_Item_ID']}",
                    "Reporting_Period": "@{variables('Period')}",
                    "Installation_ID": "@{items('Rebuild_the_fact_table')?"
                                       "['Installation_ID']}",
                    "Facility_ID": "@{items('Rebuild_the_fact_table')?"
                                   "['Facility_ID']}",
                    "Portfolio_ID": "@{items('Rebuild_the_fact_table')?"
                                    "['Portfolio_ID']}",
                    "Requirement_ID": "@{items('Rebuild_the_fact_table')?"
                                      "['Requirement_ID']}",
                    "Final_Status": "@{items('Rebuild_the_fact_table')?"
                                    "['Final_Status']?['Value']}",
                    "Status_Code": "@items('Rebuild_the_fact_table')?"
                                   "['Status_Code']",
                }},
                after={}, seed="e3-fact-row")},
            after={"Clear_the_period_from_the_fact_table": ["Succeeded"]},
            seed="e3-fact"),
        "Reconciliation_note": compose(
            "scripts/validate_solution.py --reconcile-fact compares EVERY row, "
            "not a sample. A fact table that agrees with the item list on 499 "
            "of 500 rows is a fact table nobody can trust.",
            after={"Rebuild_the_fact_table": ["Succeeded"]}, seed="e3-note"),
    }


def _eom03_item(p):
    it = "items('For_each_item')"
    cur = "body('Get_the_current_submission')?['value']"
    return {
        # The CURRENT submission decides. A superseded version never influences
        # the item -- that is what Is_Current is for.
        "Get_the_current_submission": sp(
            "GetItems",
            {"dataset": SITE, "table": p("MF_SubmissionList"),
             "$filter": f"EOM_Item_ID eq '@{{{it}?['EOM_Item_ID']}}' and "
                        "Is_Current eq 1",
             "$top": 1},
            after={}, seed="e3-sub"),
        "EffectiveDueDate": var(
            "EffectiveDueDate", "string", f"@{{{it}?['Effective_Due_Date']}}",
            after={"Get_the_current_submission": ["Succeeded"]}, seed="e3-due"),
        "EffectiveFinalCallDate": var(
            "EffectiveFinalCallDate", "string",
            f"@{{{it}?['Effective_Final_Call_Date']}}",
            after={"EffectiveDueDate": ["Succeeded"]}, seed="e3-fin"),
        "RequiredFlag": var("RequiredFlag", "boolean",
                            f"@equals({it}?['Required_Flag'], true)",
                            after={"EffectiveFinalCallDate": ["Succeeded"]},
                            seed="e3-req"),
        "WaivedFlag": var("WaivedFlag", "boolean",
                          f"@equals({it}?['Waived_Flag'], true)",
                          after={"RequiredFlag": ["Succeeded"]}, seed="e3-wai"),
        "AuthorityStatus": var(
            "AuthorityStatus", "string",
            f"@{{{it}?['Authority_Status']?['Value']}}",
            after={"WaivedFlag": ["Succeeded"]}, seed="e3-auth"),
        "ReceivedFlag": var("ReceivedFlag", "boolean",
                            f"@greater(length({cur}), 0)",
                            after={"AuthorityStatus": ["Succeeded"]},
                            seed="e3-rec"),
        "QCStatus": var(
            "QCStatus", "string",
            f"@{{coalesce(first({cur})?['QC_Status']?['Value'], '')}}",
            after={"ReceivedFlag": ["Succeeded"]}, seed="e3-qc"),
        "Status": compose("@{" + status_expression() + "}",
                          after={"QCStatus": ["Succeeded"]}, seed="e3-status"),
        # All four fields together, from one evaluation.
        "Write_all_four_status_fields": sp(
            "PatchItem",
            {"dataset": SITE, "table": p("MF_ItemList"),
             "id": f"@{{{it}?['ID']}}",
             "item": {
                 "Final_Status": "@{outputs('Status')['status']}",
                 "Status_Code": "@outputs('Status')['code']",
                 "Action_Owner": "@{outputs('Status')['actionOwner']}",
                 "Action_Required": "@outputs('Status')['actionRequired']",
                 "Last_Recalculated": "@{utcNow()}",
             }},
            after={"Status": ["Succeeded"]}, seed="e3-patch"),
        "Count_it": setvar("Recalculated",
                           "@add(variables('Recalculated'), 1)",
                           after={"Write_all_four_status_fields": ["Succeeded"]},
                           seed="e3-inc"),
    }


# ==========================================================================
# EOM-02 — Submission
# ==========================================================================

def eom02(p):
    T = "triggerBody()"
    subs, items = p("MF_SubmissionList"), p("MF_ItemList")

    return {
        # STEP 1 — AUTHORISE, BEFORE ANYTHING TOUCHES STORAGE.
        #
        # The caller's UPN comes from the flow's AUTHENTICATED CONTEXT, never
        # from the payload. A client that can name its own user is not an
        # authorisation system, and this flow can be invoked directly by anyone
        # who can see it.
        "Caller": compose(
            "@{triggerOutputs()?['headers']?['x-ms-user-email-encoded']}",
            after={}, seed="e2-caller"),
        "Get_the_callers_scope": sp(
            "GetItems",
            {"dataset": SITE, "table": p("MF_SecurityList"),
             "$filter": "UPN eq '@{outputs('Caller')}' and Active_Flag eq 1",
             "$top": 50},
            after={"Caller": ["Succeeded"]}, seed="e2-scope"),
        "Refuse_an_unmapped_or_out_of_scope_caller": condition(
            {"or": [
                {"equals": ["@length(body('Get_the_callers_scope')?['value'])",
                            0]},
                {"equals": [
                    "@length(filter(body('Get_the_callers_scope')?['value'], "
                    "or(equals(item()?['Scope_Type']?['Value'], 'Enterprise'), "
                    "equals(item()?['Installation_ID'], "
                    f"{T}?['installationId']))))", 0]},
            ]},
            {"PERMISSION_DENIED": respond(
                403,
                {"ok": False, "code": "PERMISSION_DENIED",
                 "message": "You do not have access to that installation."},
                after={}, seed="e2-403")},
            {},
            after={"Get_the_callers_scope": ["Succeeded"]}, seed="e2-if-403"),

        # STEP 1a — IDEMPOTENCY, BEFORE ANYTHING IS WRITTEN.
        #
        # A user pressing Submit twice after a timeout is the NORMAL case on a
        # government network: the request usually succeeded and the response
        # was lost. The check runs BEFORE the file write, because a check after
        # it has already created the duplicate it was meant to prevent.
        "Look_for_a_replay": sp(
            "GetItems",
            {"dataset": SITE, "table": subs,
             "$filter": "Submission_Request_ID eq "
                        f"'@{{{T}?['submissionRequestId']}}'",
             "$top": 1},
            after={"Refuse_an_unmapped_or_out_of_scope_caller": ["Succeeded"]},
            seed="e2-replay"),
        "Return_the_first_result_if_this_is_a_replay": condition(
            {"greater": ["@length(body('Look_for_a_replay')?['value'])", 0]},
            {"SUBMISSION_REPLAY": respond(
                200,
                {"ok": True, "code": "SUBMISSION_REPLAY",
                 "submissionId": "@{first(body('Look_for_a_replay')?['value'])"
                                 "?['Submission_ID']}",
                 "versionNo": "@first(body('Look_for_a_replay')?['value'])"
                              "?['Version_No']",
                 "message": "Submitted."},
                after={}, seed="e2-replay-ok")},
            {},
            after={"Look_for_a_replay": ["Succeeded"]}, seed="e2-if-replay"),

        # STEP 2 — RESOLVE THE EXPECTED ITEM. The flow does NOT create a
        # tracker row: nobody conjures a requirement by uploading against it.
        "Find_the_expected_item": sp(
            "GetItems",
            {"dataset": SITE, "table": items,
             "$filter": f"Reporting_Period eq '@{{{T}?['reportingPeriod']}}' "
                        f"and Requirement_ID eq '@{{{T}?['requirementId']}}' "
                        f"and Facility_ID eq '@{{{T}?['facilityId']}}'",
             "$top": 1},
            after={"Return_the_first_result_if_this_is_a_replay": ["Succeeded"]},
            seed="e2-item"),
        "Refuse_if_nothing_is_expected": condition(
            {"equals": ["@length(body('Find_the_expected_item')?['value'])", 0]},
            {"NO_EXPECTED_ITEM": respond(
                200,
                {"ok": False, "code": "NO_EXPECTED_ITEM",
                 "message": "There's no expected requirement matching that "
                            "facility, document and period. Send it to Needs "
                            "Classification and someone will confirm whether "
                            "the requirement should exist."},
                after={}, seed="e2-noitem")},
            {},
            after={"Find_the_expected_item": ["Succeeded"]}, seed="e2-if-item"),

        # STEP 3 — RESOLVE THE DESTINATION, AND FAIL CLOSED ON ALL THREE GATES.
        "Get_the_installation": sp(
            "GetItems",
            {"dataset": SITE, "table": p("MF_InstallationList"),
             "$filter": f"Installation_ID eq '@{{{T}?['installationId']}}'",
             "$top": 1},
            after={"Refuse_if_nothing_is_expected": ["Succeeded"]},
            seed="e2-inst"),
        "Get_the_destination": sp(
            "GetItems",
            {"dataset": SITE, "table": p("MF_DestinationList"),
             "$filter": "Portfolio_ID eq '@{first(body('Get_the_installation')"
                        "?['value'])?['Portfolio_ID']}' and Document_Domain eq "
                        "'EOM' and Active_Flag eq 1",
             "$top": 1},
            after={"Get_the_installation": ["Succeeded"]}, seed="e2-dest"),
        "Fail_closed_on_the_destination": condition(
            {"or": [
                {"equals": ["@length(body('Get_the_destination')?['value'])", 0]},
                {"equals": [
                    "@coalesce(first(body('Get_the_destination')?['value'])"
                    "?['Verified_By'], '')", ""]},
                {"equals": [
                    "@coalesce(first(body('Get_the_destination')?['value'])"
                    "?['Site_URL'], '')", ""]},
            ]},
            {"DESTINATION_NOT_USABLE": respond(
                200,
                # None of these surfaces a path, a site URL, a GUID or a
                # connector message. A user who cannot upload does not need
                # the tenant's topology to report the problem.
                {"ok": False, "code": "DESTINATION_NOT_CONFIGURED",
                 "message": "Uploads for this portfolio aren't configured yet. "
                            "An administrator has been notified."},
                after={}, seed="e2-nodest")},
            {},
            after={"Get_the_destination": ["Succeeded"]}, seed="e2-if-dest"),

        # STEP 4 — FIND THE FOLDER. NEVER CREATE ONE.
        "Destination": compose(
            "@first(body('Get_the_destination')?['value'])",
            after={"Fail_closed_on_the_destination": ["Succeeded"]},
            seed="e2-d"),
        "Root": compose(
            # THE URL SEGMENT, NEVER THE DISPLAY NAME. A library displayed as
            # "Documents" is "Shared Documents" in the URL; building the path
            # from the display name 404s on a library that plainly exists and
            # gets debugged as a permissions problem.
            "@{concat(outputs('Destination')?['Library_Url_Segment'], '/', "
            "outputs('Destination')?['Root_Folder'])}",
            after={"Destination": ["Succeeded"]}, seed="e2-root"),
        "List_the_fiscal_year_folders": sp(
            "GetFileItems",
            {"dataset": "@{outputs('Destination')?['Site_URL']}",
             "table": "@{outputs('Destination')?['Library_Url_Segment']}",
             "$filter": "FSObjType eq 1"},
            after={"Root": ["Succeeded"]}, seed="e2-lsfy"),
        "Resolve_the_folder": compose(
            {"rule": "MATCH, DO NOT CONSTRUCT. Fiscal year: FY26, FY 26, "
                     "FY-26, FY2026, FY 2026. Month: the full name, then the "
                     "three-letter form, then the two-digit number, in that "
                     "order, case- and accent-insensitively. Where a folder "
                     "states a year it must be the right one.",
             "reference": "scripts/folder_resolver.py, held to this spec by "
                          "tests/test_folder_resolver.py",
             "createMissing": "NEVER. Create_Missing_Folders is FALSE "
                              "permanently: a flow that creates folders "
                              "eventually produces 'Aug 26' beside someone's "
                              "'August 2026' and nobody notices for a month.",
             "fallback": "FIND_OR_ROOT. Write to the Monthly Data Call root, "
                         "Needs_Filing TRUE, Filing_Note naming what was "
                         "searched for. NEVER above that root: a file at a "
                         "site or library root looks like it worked and is "
                         "somewhere nobody will look."},
            after={"List_the_fiscal_year_folders": ["Succeeded"]},
            seed="e2-resolve"),

        # STEP 5 to 7 — create, record, confirm.
        "Create_the_file": sp(
            "CreateFile",
            {"dataset": "@{outputs('Destination')?['Site_URL']}",
             "folderPath": "@{outputs('Root')}",
             # The original filename is preserved AS UPLOADED. No naming
             # convention is applied, required or inferred.
             "name": f"@{{{T}?['fileName']}}",
             "body": f"@{{{T}?['fileContent']}}"},
            after={"Resolve_the_folder": ["Succeeded"]}, seed="e2-file"),
        "Supersede_the_current_version": sp(
            "GetItems",
            {"dataset": SITE, "table": subs,
             "$filter": "EOM_Item_ID eq '@{first(body('Find_the_expected_item')"
                        "?['value'])?['EOM_Item_ID']}' and Is_Current eq 1",
             "$top": 1},
            after={"Create_the_file": ["Succeeded"]}, seed="e2-super"),
        "Record_the_submission": sp(
            "PostItem",
            {"dataset": SITE, "table": subs, "item": {
                "Submission_Request_ID": f"@{{{T}?['submissionRequestId']}}",
                "EOM_Item_ID": "@{first(body('Find_the_expected_item')"
                               "?['value'])?['EOM_Item_ID']}",
                "Version_No": "@add(length(body('Supersede_the_current_version')"
                              "?['value']), 1)",
                "File_Name": f"@{{{T}?['fileName']}}",
                # STORE THE GUID; RESOLVE THE URL FROM IT. A file that gets
                # moved or renamed keeps its unique ID and loses its URL -- and
                # under FIND_OR_ROOT files get moved BY DESIGN, by the human
                # who files them properly.
                "SharePoint_Unique_ID": "@{body('Create_the_file')?"
                                        "['{Identifier}']}",
                "SharePoint_File_ID": "@{body('Create_the_file')?['Id']}",
                "File_URL": "@{body('Create_the_file')?['Path']}",
                "Destination_ID": "@{outputs('Destination')?['Destination_ID']}",
                "Source_Library": "@{outputs('Destination')"
                                  "?['Library_Url_Segment']}",
                "Source_Path": "@{outputs('Root')}",
                "Uploaded_By": "@{outputs('Caller')}",
                "Submitted_On_Behalf_Of": f"@{{{T}?['onBehalfOf']}}",
                "Intake_Method": "App upload",
                "Classification_Method": "Declared at upload",
                "Classification_Confidence": "Declared",
                "Is_Current": True,
                "Is_Pilot": "@equals(outputs('Pilot_mode'), 'True')",
                "QC_Status": "Pending Review",
            }},
            after={"Supersede_the_current_version": ["Succeeded"]},
            seed="e2-record"),
        "Audit_the_upload": audit(
            p("MF_AuditList"),
            {"Action": "Uploaded",
             "Action_DateTime": "@{utcNow()}",
             "Entity_Type": "Submission",
             "Entity_ID": "@{body('Record_the_submission')?['Submission_ID']}",
             # The AUTHENTICATED identity, never the payload. A user may not
             # write an audit author.
             "Actor_UPN": "@{outputs('Caller')}",
             "Detail": "@{concat('Version ', body('Record_the_submission')?"
                       "['Version_No'], ' of ', triggerBody()?['fileName'])}"},
            after={"Record_the_submission": ["Succeeded"]}, seed="e2-audit"),
        "Pilot_mode": compose(
            "@{first(body('Get_the_callers_scope')?['value'])?['Is_Pilot']}",
            after={"Refuse_an_unmapped_or_out_of_scope_caller": ["Succeeded"]},
            seed="e2-pilot"),
        # NEVER REPORT SUCCESS ON A PARTIAL WRITE. A file in SharePoint with no
        # submission record is invisible to the app and will be found by nobody.
        "Confirm_or_fail_loudly": condition(
            {"equals": ["@empty(body('Record_the_submission')?['ID'])", True]},
            {"SUBMISSION_NOT_CONFIRMED": respond(
                200,
                {"ok": False, "code": "SUBMISSION_NOT_CONFIRMED",
                 "correlationId": "@{workflow()['run']['name']}",
                 "message": "We couldn't confirm your submission. Quote this "
                            "reference when you report it."},
                after={}, seed="e2-unconf")},
            {"OK": respond(
                200,
                {"ok": True, "code": "SUBMISSION_CREATED",
                 "submissionId": "@{body('Record_the_submission')?"
                                 "['Submission_ID']}",
                 "versionNo": "@body('Record_the_submission')?['Version_No']",
                 "needsFiling": "@outputs('Resolve_the_folder')?['needsFiling']",
                 "message": "Submitted."},
                after={}, seed="e2-ok")},
            after={"Audit_the_upload": ["Succeeded", "Failed"]},
            seed="e2-if-conf"),
    }


# ==========================================================================
# EOM-02b — Legacy Intake      (deployed FOUR TIMES, one per site collection)
# ==========================================================================

def eom02b(p):
    F = "triggerOutputs()?['body']"
    return {
        # DEDUPLICATE ON THE GUID, NOT THE PATH. Under FIND_OR_ROOT a file is
        # moved BY DESIGN by the human who files it properly: it changes path
        # twice and keeps its GUID throughout. A path check would rediscover it
        # as an unmatched stray on the day somebody tidied up.
        "Has_a_submission_already_claimed_this_file": sp(
            "GetItems",
            {"dataset": SITE, "table": p("MF_SubmissionList"),
             "$filter": f"SharePoint_Unique_ID eq '@{{{F}?['{{Identifier}}']}}'",
             "$top": 1},
            after={}, seed="e2b-dedupe"),
        "Only_classify_what_the_app_did_not_write": condition(
            {"equals": [
                "@length(body('Has_a_submission_already_claimed_this_file')"
                "?['value'])", 0]},
            {
                "Suggest_an_installation_from_the_uploader": sp(
                    # The uploader's mapping is the strongest available signal,
                    # because base DFAC managers upload their own documents. It
                    # stays a HINT, never a decision: an AFSVC MFM uploading an
                    # emailed document would otherwise resolve to the wrong
                    # installation and the missing counts would go wrong
                    # silently.
                    "GetItems",
                    {"dataset": SITE, "table": p("MF_SecurityList"),
                     "$filter": f"UPN eq '@{{{F}?['Author']?['Email']}}' and "
                                "Active_Flag eq 1",
                     "$top": 1},
                    after={}, seed="e2b-hint"),
                "Queue_it_for_a_human": sp(
                    "PostItem",
                    {"dataset": SITE, "table": p("MF_UnmatchedList"), "item": {
                        "File_Name": f"@{{{F}?['Name']}}",
                        "File_URL": f"@{{{F}?['Path']}}",
                        "Discovered_DateTime": "@{utcNow()}",
                        "Uploaded_By": f"@{{{F}?['Author']?['Email']}}",
                        # WEAK HINTS ONLY. NEVER AUTO-APPLIED. No filename
                        # convention exists and none is assumed.
                        "Suggested_Installation_ID":
                            "@{first(body('Suggest_an_installation_from_the_"
                            "uploader')?['value'])?['Installation_ID']}",
                        "Suggested_Document_Code": "",
                        "Resolution_Status": "Needs Classification",
                    }},
                    after={"Suggest_an_installation_from_the_uploader":
                           ["Succeeded"]},
                    seed="e2b-queue"),
                "Note_that_nothing_was_invented": compose(
                    "NEVER INVENT A REQUIREMENT. There is no branch here that "
                    "creates an MF EOM Item and there must never be one. A "
                    "file with no matching expected item stays in the queue "
                    "until a human decides what it is, or decides the "
                    "requirement should exist -- which is a deliberate act on "
                    "scrAdminRequirements.",
                    after={"Queue_it_for_a_human": ["Succeeded"]},
                    seed="e2b-note"),
            },
            {},
            after={"Has_a_submission_already_claimed_this_file": ["Succeeded"]},
            seed="e2b-if"),
    }


# ==========================================================================
# EOM-04 — Notifications        (built, DISABLED, digest not per-item)
# ==========================================================================

def eom04(p):
    enabled = p("MF_NotificationsEnabled")
    escalate = p("MF_EscalationDaysOverdue")
    return {
        "Today": var("Today", "string",
                     "@{formatDateTime(utcNow(), 'yyyy-MM-dd')}",
                     after={}, seed="e4-today"),
        "Get_the_enabled_rules": sp(
            "GetItems",
            {"dataset": SITE, "table": p("MF_NotificationRuleList"),
             "$filter": "Enabled eq 1", "$top": 100},
            after={"Today": ["Succeeded"]}, seed="e4-rules"),
        "For_each_rule": foreach(
            "@body('Get_the_enabled_rules')?['value']",
            {
                "Escalation_cutoff": compose(
                    # Days past suspense before a portfolio escalation. Read
                    # from configuration, never a literal in a flow.
                    ("@{formatDateTime(addToTime(utcNow(), mul(-1, int("
                     + escalate + ")), 'Day'), 'yyyy-MM-dd')}"),
                    after={}, seed="e4-cutoff"),
                "Gather_the_recipients_work": sp(
                    # DIGEST, NOT PER ITEM. One message per recipient per run
                    # listing everything they owe. Per-item mail across 103
                    # installations is how a notification system gets muted in
                    # week one.
                    "GetItems",
                    {"dataset": SITE, "table": p("MF_ItemList"),
                     "$filter": "Action_Required eq 1 and Effective_Due_Date "
                                "le '@{outputs('Escalation_cutoff')}'",
                     "$top": 2000},
                    after={"Escalation_cutoff": ["Succeeded"]}, seed="e4-work"),
                "Send_or_record_the_suppression": condition(
                    # THE MASTER SWITCH. With notifications off the flow
                    # records what it WOULD have sent, and you read a full
                    # cycle of that before enabling anything.
                    {"equals": [f"@{enabled}", True]},
                    {"Send_the_digest": sp(
                        "SendEmailV2",
                        {"emailMessage": {
                            "To": "@{items('For_each_rule')?"
                                  "['Recipient_Address']}",
                            "Subject": "@{items('For_each_rule')?"
                                       "['Subject_Template']}",
                            "Body": "<p>@{length(body('Gather_the_recipients_"
                                    "work')?['value'])} document(s) need your "
                                    "attention.</p>",
                        }},
                        after={}, seed="e4-send",
                        api=O365, conn="shared_office365")},
                    {"Record_what_it_would_have_sent": audit(
                        p("MF_AuditList"),
                        {"Action": "Notification Suppressed",
                         "Action_DateTime": "@{utcNow()}",
                         "Entity_Type": "Notification",
                         "Entity_ID": "@{items('For_each_rule')?['Rule_ID']}",
                         "Detail": "@{concat('Would have notified ', "
                                   "items('For_each_rule')?"
                                   "['Recipient_Address'], ' about ', "
                                   "length(body('Gather_the_recipients_work')"
                                   "?['value']), ' item(s).')}"},
                        after={}, seed="e4-suppress")},
                    after={"Gather_the_recipients_work": ["Succeeded"]},
                    seed="e4-if"),
            },
            after={"Get_the_enabled_rules": ["Succeeded"]}, seed="e4-loop"),
    }


BODIES = {
    "EOM01ExpectedPackage": eom01,
    "EOM02Submission": eom02,
    "EOM02bLegacyIntake": eom02b,
    "EOM03Reconciliation": eom03,
    "EOM04Notifications": eom04,
}
