#!/usr/bin/env python3
"""Build a real, importable unmanaged solution package under solution/src.

    python3 scripts/gen_solution_package.py

Produces, hand-authored against the documented schemas:

    solution/src/[Content_Types].xml
    solution/src/Other/Solution.xml
    solution/src/Other/Customizations.xml
    solution/src/Workflows/<Flow>-<guid>.json          five cloud flows

WHAT IS DELIBERATELY ABSENT
---------------------------
**There is no .msapp and there is no placeholder for one.**

The canvas app's internal format is owned by Power Apps Studio, `pac canvas
pack` is being deprecated, and the source format is mid-transition. A
hand-authored file with the right extension that Studio rejects on open is
worse than no file at all: the import fails with an error naming an internal
file and explaining nothing, and whoever is holding it spends an afternoon
assuming the tenant is at fault.

So the package ships without it, `CANVAS_APP_ASSEMBLY.md` says how to create
the app *inside* the imported solution, and it inherits these connection
references and environment variables the moment it is created.

WHAT THE FLOWS ARE, HONESTLY
----------------------------
Each flow carries its real trigger, its real connection reference bindings, its
environment-variable reads and the schema-compatibility guard every flow must
perform. **The body of each is not implemented here.** The specifications in
`flows/*/definition.md` are the source, and a flow whose logic was invented to
fill a JSON file would be worse than an obviously unfinished one.

Every flow therefore begins with a Compose action naming its specification, and
every flow imports **disabled** — which is what `docs/DEPLOYMENT.md` requires
anyway: flows are enabled one at a time, in order, after EOM-01 is proven.

GUIDs are derived deterministically from the flow name, so rebuilding the same
tag produces the same bytes.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "solution", "src")
CONFIG = os.path.join(ROOT, "configuration")

PUBLISHER = "MissionFeeding"
PREFIX = "mfops"
UNIQUE_NAME = "MissionFeedingOperations"

# A fixed namespace: the same flow name always yields the same GUID, so a
# rebuild of the same tag is byte-identical and a re-import updates the flow
# that is already there rather than creating a second one.
NS = uuid.UUID("6f1e5b9a-6d2c-5f7e-9a3b-6c1d4e2f8a70")


def guid(name):
    return str(uuid.uuid5(NS, name)).lower()


def load(name):
    with open(os.path.join(CONFIG, name), encoding="utf-8") as fh:
        return json.load(fh)


def version():
    import csv
    with open(os.path.join(CONFIG, "app-config.csv"), encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["Config_Key"] == "AppVersion":
                return r["Config_Value"]
    raise SystemExit("AppVersion not found in app-config.csv")


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


# --------------------------------------------------------------------------
# Flows
# --------------------------------------------------------------------------

FLOWS = [
    {
        "schema": "EOM01ExpectedPackage",
        "display": "EOM-01 Expected Package Generator",
        "spec": "flows/EOM01-ExpectedPackage/definition.md",
        "purpose": "Create the expected MF_EOM_Item rows for the open period.",
        "trigger": {
            "kind": "Recurrence",
            "json": {
                "type": "Recurrence",
                "recurrence": {"frequency": "Month", "interval": 1,
                               "schedule": {"monthDays": [1], "hours": ["5"],
                                            "minutes": [0]}},
                "metadata": {"operationMetadataId": guid("EOM01-trigger")},
            },
        },
        "connections": ["sharepointonline"],
    },
    {
        "schema": "EOM02Submission",
        "display": "EOM-02 Submission",
        "spec": "flows/EOM02-Submission/definition.md",
        "purpose": ("Resolve the destination, place the file, write the "
                    "submission row. Called by scrUpload."),
        "trigger": {
            "kind": "Request",
            "json": {
                "type": "Request",
                "kind": "PowerApp",
                "inputs": {"schema": {
                    "type": "object",
                    "properties": {
                        "submissionRequestId": {"type": "string",
                                                "title": "Submission_Request_ID",
                                                "x-ms-content-hint": "TEXT"},
                        "installationId": {"type": "string", "x-ms-content-hint": "TEXT"},
                        "reportingPeriod": {"type": "string", "x-ms-content-hint": "TEXT"},
                        "requirementId": {"type": "string", "x-ms-content-hint": "TEXT"},
                        "facilityId": {"type": "string", "x-ms-content-hint": "TEXT"},
                        "fileName": {"type": "string", "x-ms-content-hint": "TEXT"},
                        "fileContent": {"type": "string", "format": "byte",
                                        "x-ms-content-hint": "FILE"},
                        "onBehalfOf": {"type": "string", "x-ms-content-hint": "TEXT"},
                        "note": {"type": "string", "x-ms-content-hint": "TEXT"},
                    },
                    "required": ["submissionRequestId", "installationId",
                                 "reportingPeriod", "requirementId",
                                 "fileName", "fileContent"],
                }},
                "metadata": {"operationMetadataId": guid("EOM02-trigger")},
            },
        },
        "connections": ["sharepointonline"],
        "note": ("uploadedBy is NOT an input. The caller's UPN comes from the "
                 "flow's authenticated context: a client that can name its own "
                 "user is not an authorisation system."),
    },
    {
        "schema": "EOM02bLegacyIntake",
        "display": "EOM-02b Legacy Intake",
        "spec": "flows/EOM02b-LegacyIntake/definition.md",
        "purpose": ("Catch folder drops the app did not create. DEPLOY FOUR "
                    "TIMES, once per portfolio site collection."),
        "trigger": {
            "kind": "SharePointFileCreated",
            "json": {
                "type": "OpenApiConnection",
                "inputs": {
                    "host": {"connectionName": "shared_sharepointonline",
                             "operationId": "OnNewFileV2",
                             "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"},
                    "parameters": {
                        "dataset": "@parameters('MF_Portfolio1_SiteURL (mfops_MF_Portfolio1_SiteURL)')",
                        "table": "Shared Documents",
                    },
                    "authentication": "@parameters('$authentication')",
                },
                "recurrence": {"frequency": "Minute", "interval": 15},
                "metadata": {"operationMetadataId": guid("EOM02b-trigger")},
            },
        },
        "connections": ["sharepointonline"],
        "note": ("A SharePoint trigger binds to ONE site. The four portfolios "
                 "are four separate site collections, so this flow is deployed "
                 "four times, each bound to its own MF_Portfolio{n}_SiteURL. "
                 "One instance covering all four is not an option the "
                 "connector offers."),
    },
    {
        "schema": "EOM03Reconciliation",
        "display": "EOM-03 Reconciliation",
        "spec": "flows/EOM03-Reconciliation/definition.md",
        "purpose": ("Recalculate Final_Status and Status_Code, rebuild "
                    "MF_EOM_Status."),
        "trigger": {
            "kind": "Recurrence",
            "json": {
                "type": "Recurrence",
                "recurrence": {"frequency": "Day", "interval": 1,
                               "schedule": {"hours": ["2"], "minutes": [0]}},
                "metadata": {"operationMetadataId": guid("EOM03-trigger")},
            },
        },
        "connections": ["sharepointonline"],
    },
    {
        "schema": "EOM04Notifications",
        "display": "EOM-04 Notifications",
        "spec": "flows/EOM04-Notifications/definition.md",
        "purpose": "Suspense reminders and escalation. SHIPS DISABLED.",
        "trigger": {
            "kind": "Recurrence",
            "json": {
                "type": "Recurrence",
                "recurrence": {"frequency": "Day", "interval": 1,
                               "schedule": {"hours": ["7"], "minutes": [0]}},
                "metadata": {"operationMetadataId": guid("EOM04-trigger")},
            },
        },
        "connections": ["sharepointonline", "office365"],
        "note": ("MF_NotificationsEnabled gates every send. With it FALSE the "
                 "flow records what it WOULD have sent to MF_EOM_Audit as "
                 "'Notification Suppressed'. Read a full cycle of that before "
                 "enabling anything."),
    },
]

CONNECTOR_API = {
    "sharepointonline": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
    "office365users": "/providers/Microsoft.PowerApps/apis/shared_office365users",
    "office365": "/providers/Microsoft.PowerApps/apis/shared_office365",
}

# Which environment variables each flow reads. Declared as workflow parameters
# so the flow binds to the solution's variables rather than a literal.
FLOW_ENV_VARS = {
    "EOM01ExpectedPackage": ["mfops_MF_SharePointSiteURL", "mfops_MF_ConfigList",
                             "mfops_MF_RequirementList", "mfops_MF_ItemList",
                             "mfops_MF_CurrentFiscalYear"],
    "EOM02Submission": ["mfops_MF_SharePointSiteURL", "mfops_MF_ConfigList",
                        "mfops_MF_ItemList", "mfops_MF_SubmissionList",
                        "mfops_MF_SecurityList", "mfops_MF_AuditList",
                        "mfops_MF_Portfolio1_SiteURL", "mfops_MF_Portfolio2_SiteURL",
                        "mfops_MF_Portfolio3_SiteURL", "mfops_MF_Portfolio4_SiteURL"],
    "EOM02bLegacyIntake": ["mfops_MF_SharePointSiteURL", "mfops_MF_ConfigList",
                           "mfops_MF_UnmatchedList", "mfops_MF_SubmissionList",
                           "mfops_MF_Portfolio1_SiteURL"],
    "EOM03Reconciliation": ["mfops_MF_SharePointSiteURL", "mfops_MF_ConfigList",
                            "mfops_MF_ItemList", "mfops_MF_StatusList"],
    "EOM04Notifications": ["mfops_MF_SharePointSiteURL", "mfops_MF_ConfigList",
                           "mfops_MF_ItemList", "mfops_MF_AuditList",
                           "mfops_MF_NotificationsEnabled",
                           "mfops_MF_EscalationDaysOverdue"],
}


def env_var_display(schema_name, env_vars):
    for v in env_vars:
        if v["schemaName"] == schema_name:
            return v["displayName"]
    raise KeyError(schema_name)


def flow_definition(flow, env_vars):
    """A real workflow definition: real trigger, real bindings, real guard.

    The BODY is not invented here. See the module docstring.
    """
    params = {
        "$connections": {"defaultValue": {}, "type": "Object"},
        "$authentication": {"defaultValue": {}, "type": "SecureObject"},
    }
    for schema_name in FLOW_ENV_VARS[flow["schema"]]:
        display = env_var_display(schema_name, env_vars)
        params[f"{display} ({schema_name})"] = {
            "defaultValue": "", "type": "String",
            "metadata": {"schemaName": schema_name},
        }

    site = "@parameters('MF_SharePointSiteURL (mfops_MF_SharePointSiteURL)')"
    cfg = "@parameters('MF_ConfigList (mfops_MF_ConfigList)')"

    actions = {
        "READ_THE_SPECIFICATION_FIRST": {
            "type": "Compose",
            "runAfter": {},
            "inputs": {
                "flow": flow["display"],
                "purpose": flow["purpose"],
                "specification": flow["spec"],
                "status": ("TRIGGER, CONNECTIONS AND ENVIRONMENT VARIABLES ARE "
                           "WIRED. THE BODY IS NOT IMPLEMENTED."),
                "why": ("The logic is specified in the file named above and was "
                        "not invented to fill this JSON. A flow whose body was "
                        "guessed would import cleanly and do the wrong thing, "
                        "which is worse than one that is obviously unfinished."),
                "note": flow.get("note", ""),
            },
            "metadata": {"operationMetadataId": guid(flow["schema"] + "-readme")},
        },
        # Every flow makes this comparison independently. The app disabling its
        # own submit button is not a control: a flow can be invoked directly,
        # and a scheduled flow has no app in front of it at all.
        "Get_the_deployed_schema_version": {
            "type": "OpenApiConnection",
            "runAfter": {"READ_THE_SPECIFICATION_FIRST": ["Succeeded"]},
            "inputs": {
                "host": {"connectionName": "shared_sharepointonline",
                         "operationId": "GetItems",
                         "apiId": CONNECTOR_API["sharepointonline"]},
                "parameters": {
                    "dataset": site,
                    "table": cfg,
                    "$filter": "Config_Key eq 'SchemaVersion'",
                    "$top": 1,
                },
                "authentication": "@parameters('$authentication')",
            },
            "metadata": {"operationMetadataId": guid(flow["schema"] + "-schema")},
        },
        "Stop_on_a_schema_mismatch": {
            "type": "If",
            "runAfter": {"Get_the_deployed_schema_version": ["Succeeded"]},
            "expression": {"not": {"equals": [
                "@first(body('Get_the_deployed_schema_version')?['value'])?['Config_Value']",
                "@variables('ExpectedSchemaVersion')",
            ]}},
            "actions": {
                "CONFIGURATION_REQUIRED": {
                    "type": "Terminate",
                    "runAfter": {},
                    "inputs": {
                        "runStatus": "Failed",
                        "runError": {
                            "code": "CONFIGURATION_REQUIRED",
                            "message": ("This flow expects a different schema "
                                        "version than MF_App_Config reports. A "
                                        "newer flow writing against an older "
                                        "schema patches columns that do not "
                                        "exist, which writes nothing rather "
                                        "than erroring. Stopped before any "
                                        "write. See "
                                        "docs/SHAREPOINT_SCHEMA_MANIFEST.md."),
                        },
                    },
                    "metadata": {"operationMetadataId": guid(flow["schema"] + "-term")},
                },
            },
            "else": {"actions": {}},
            "metadata": {"operationMetadataId": guid(flow["schema"] + "-if")},
        },
    }

    return {
        "properties": {
            "connectionReferences": {
                f"shared_{c}": {
                    "runtimeSource": "embedded",
                    "connection": {"connectionReferenceLogicalName": f"{PREFIX}_{c}"},
                    "api": {"name": f"shared_{c}"},
                }
                for c in flow["connections"]
            },
            "definition": {
                "$schema": ("https://schema.management.azure.com/providers/"
                            "Microsoft.Logic/schemas/2016-06-01/"
                            "workflowdefinition.json#"),
                "contentVersion": "1.0.0.0",
                "parameters": params,
                "triggers": {flow["trigger"]["kind"]: flow["trigger"]["json"]},
                "actions": {
                    "Initialize_ExpectedSchemaVersion": {
                        "type": "InitializeVariable",
                        "runAfter": {},
                        "inputs": {"variables": [{
                            "name": "ExpectedSchemaVersion",
                            "type": "string",
                            # A literal, deliberately. Reading it from the
                            # environment would compare a value with itself.
                            "value": schema_version(),
                        }]},
                        "metadata": {"operationMetadataId": guid(flow["schema"] + "-var")},
                    },
                    **{k: (v if k == "READ_THE_SPECIFICATION_FIRST" else v)
                       for k, v in actions.items()},
                },
                "outputs": {},
            },
        },
        "schemaVersion": "1.0.0.0",
    }


def schema_version():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import eom_schema
    return eom_schema.SCHEMA_VERSION


# --------------------------------------------------------------------------
# The XML
# --------------------------------------------------------------------------

CONTENT_TYPES = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="text/xml" />
  <Default Extension="json" ContentType="application/octet-stream" />
</Types>
'''


def solution_xml(ver, env_vars, conn_refs):
    parts = []
    for f in FLOWS:
        parts.append(f'      <RootComponent type="29" id="{{{guid(f["schema"])}}}" '
                     f'behavior="0" />')
    for c in conn_refs:
        parts.append(f'      <RootComponent type="10108" '
                     f'schemaName="{c["schemaName"]}" behavior="0" />')
    for v in env_vars:
        parts.append(f'      <RootComponent type="380" '
                     f'schemaName="{v["schemaName"]}" behavior="0" />')
    components = "\n".join(parts)

    return f'''<?xml version="1.0" encoding="utf-8"?>
<!--
  GENERATED by scripts/gen_solution_package.py. Do not edit by hand.

  MissionFeedingOperations solution manifest.

  THE CANVAS APP IS NOT IN THIS PACKAGE AND THERE IS NO PLACEHOLDER FOR IT.
  The app is created inside this solution after import, in Power Apps Studio,
  where it inherits the connection references and environment variables
  declared below. See CANVAS_APP_ASSEMBLY.md.

  Note for anyone editing these comments: a double hyphen is illegal inside an
  XML comment and makes this file unparseable, which fails the import before it
  starts.
-->
<ImportExportXml version="9.2.24091.183" SolutionPackageVersion="9.2" languagecode="1033" generatedBy="CrmLive">
  <SolutionManifest>
    <UniqueName>{UNIQUE_NAME}</UniqueName>
    <LocalizedNames>
      <LocalizedName description="Mission Feeding Operations" languagecode="1033" />
    </LocalizedNames>
    <Descriptions>
      <Description description="End of month and end of year document requirement, evidence, versioning, QC and common operational picture for mission feeding facilities. Release 1. Flows, environment variables and connection references only; the canvas app is created inside this solution after import." languagecode="1033" />
    </Descriptions>
    <Version>{ver}</Version>
    <Managed>0</Managed>
    <Publisher>
      <UniqueName>{PUBLISHER}</UniqueName>
      <LocalizedNames>
        <LocalizedName description="Mission Feeding" languagecode="1033" />
      </LocalizedNames>
      <Descriptions>
        <Description description="Air Force Services Center, Mission Feeding" languagecode="1033" />
      </Descriptions>
      <EMailAddress xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
      <SupportingWebsiteUrl xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
      <CustomizationPrefix>{PREFIX}</CustomizationPrefix>
      <CustomizationOptionValuePrefix>21400</CustomizationOptionValuePrefix>
      <Addresses>
        <Address>
          <AddressNumber>1</AddressNumber>
          <AddressTypeCode>1</AddressTypeCode>
          <City xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <County xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Country xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Fax xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <FreightTermsCode xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <ImportSequenceNumber xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Latitude xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Line1 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Line2 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Line3 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Longitude xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Name xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <PostalCode xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <PostOfficeBox xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <PrimaryContactName xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <ShippingMethodCode xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <StateOrProvince xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Telephone1 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Telephone2 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Telephone3 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <TimeZoneRuleVersionNumber xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <UPSZone xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <UTCOffset xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <UTCConversionTimeZoneCode xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
        </Address>
        <Address>
          <AddressNumber>2</AddressNumber>
          <AddressTypeCode>1</AddressTypeCode>
          <City xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <County xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Country xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Fax xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <FreightTermsCode xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <ImportSequenceNumber xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Latitude xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Line1 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Line2 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Line3 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Longitude xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Name xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <PostalCode xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <PostOfficeBox xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <PrimaryContactName xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <ShippingMethodCode xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <StateOrProvince xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Telephone1 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Telephone2 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <Telephone3 xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <TimeZoneRuleVersionNumber xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <UPSZone xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <UTCOffset xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
          <UTCConversionTimeZoneCode xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" />
        </Address>
      </Addresses>
    </Publisher>
    <RootComponents>
{components}
    </RootComponents>
    <MissingDependencies />
  </SolutionManifest>
</ImportExportXml>
'''


TYPE_CODE = {"String": "100000000", "Number": "100000001",
             "Boolean": "100000002", "JSON": "100000003",
             "Data source": "100000004", "Secret": "100000005"}


def customizations_xml(env_vars, conn_refs):
    wf = []
    for f in FLOWS:
        g = guid(f["schema"])
        wf.append(f'''    <Workflow WorkflowId="{{{g}}}" Name="{esc(f["display"])}">
      <JsonFileName>/Workflows/{f["schema"]}-{g.upper()}.json</JsonFileName>
      <Type>1</Type>
      <Subprocess>0</Subprocess>
      <Category>5</Category>
      <Mode>0</Mode>
      <Scope>4</Scope>
      <OnDemand>0</OnDemand>
      <TriggerOnCreate>0</TriggerOnCreate>
      <TriggerOnDelete>0</TriggerOnDelete>
      <AsyncAutodelete>0</AsyncAutodelete>
      <SyncWorkflowLogOnFailure>0</SyncWorkflowLogOnFailure>
      <StateCode>0</StateCode>
      <StatusCode>1</StatusCode>
      <RunAs>1</RunAs>
      <IsTransacted>1</IsTransacted>
      <IntroducedVersion>1.0</IntroducedVersion>
      <IsCustomizable>1</IsCustomizable>
      <BusinessProcessType>0</BusinessProcessType>
      <IsCustomProcessingStepAllowedForOtherPublishers>1</IsCustomProcessingStepAllowedForOtherPublishers>
      <PrimaryEntity>none</PrimaryEntity>
      <LocalizedNames>
        <LocalizedName description="{esc(f["display"])}" languagecode="1033" />
      </LocalizedNames>
    </Workflow>''')

    cr = []
    for c in conn_refs:
        cr.append(f'''    <connectionreference connectionreferencelogicalname="{c["schemaName"]}">
      <connectionreferencedisplayname>{esc(c["displayName"])}</connectionreferencedisplayname>
      <connectorid>{c["connectorId"]}</connectorid>
      <iscustomizable>1</iscustomizable>
      <statecode>0</statecode>
      <statuscode>1</statuscode>
    </connectionreference>''')

    ev = []
    for v in env_vars:
        required = "0" if v["schemaName"] == "mfops_MF_PowerBIReportURL" else "1"
        ev.append(f'''    <environmentvariabledefinition schemaname="{v["schemaName"]}">
      <displayname>{esc(v["displayName"])}</displayname>
      <description>{esc(v["description"])}</description>
      <type>{TYPE_CODE[v["type"]]}</type>
      <isrequired>{required}</isrequired>
      <introducedversion>1.0</introducedversion>
      <iscustomizable>1</iscustomizable>
      <environmentvariablevalues />
    </environmentvariabledefinition>''')

    nl = "\n"
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!--
  GENERATED by scripts/gen_solution_package.py. Do not edit by hand.

  EVERY ENVIRONMENT VARIABLE SHIPS WITH NO VALUE. environmentvariablevalues is
  empty on all {len(env_vars)} of them, deliberately: a value committed here is a
  destination baked into the package, and a .mil site URL in source is a
  destination leak. Values are supplied at import from a deployment settings
  file kept out of source control.

  The four MF_Portfolio*_SiteURL variables are four SEPARATE SITE COLLECTIONS,
  not four folders in one library, and their slugs are not consistent. Portfolio
  2 carries a Legacy_ prefix the other three do not, so a URL built by pattern
  404s on exactly one portfolio. See deployment/site-bindings.md.

  Note for anyone editing these comments: a double hyphen is illegal inside an
  XML comment and makes this file unparseable.
-->
<ImportExportXml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Entities />
  <Roles />
  <Workflows>
{nl.join(wf)}
  </Workflows>
  <FieldSecurityProfiles />
  <Templates />
  <EntityMaps />
  <EntityRelationships />
  <OrganizationSettings />
  <optionsets />
  <CustomControls />
  <EntityDataProviders />
  <connectionreferences>
{nl.join(cr)}
  </connectionreferences>
  <environmentvariabledefinitions>
{nl.join(ev)}
  </environmentvariabledefinitions>
  <Languages>
    <Language>1033</Language>
  </Languages>
</ImportExportXml>
'''


def main():
    env_vars = load("environment-variables.json")["environmentVariables"]
    conn_refs = load("connection-references.json")["connectionReferences"]
    ver = version()

    # Rebuild from scratch so a removed component cannot linger.
    for sub in ("Other", "Workflows"):
        shutil.rmtree(os.path.join(SRC, sub), ignore_errors=True)
    os.makedirs(os.path.join(SRC, "Other"), exist_ok=True)
    os.makedirs(os.path.join(SRC, "Workflows"), exist_ok=True)

    with open(os.path.join(SRC, "[Content_Types].xml"), "w", encoding="utf-8") as fh:
        fh.write(CONTENT_TYPES)
    with open(os.path.join(SRC, "Other", "Solution.xml"), "w", encoding="utf-8") as fh:
        fh.write(solution_xml(ver, env_vars, conn_refs))
    with open(os.path.join(SRC, "Other", "Customizations.xml"), "w", encoding="utf-8") as fh:
        fh.write(customizations_xml(env_vars, conn_refs))

    for f in FLOWS:
        g = guid(f["schema"])
        path = os.path.join(SRC, "Workflows", f'{f["schema"]}-{g.upper()}.json')
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(flow_definition(f, env_vars), fh, indent=2)
            fh.write("\n")

    print(f"solution {UNIQUE_NAME} {ver}")
    print(f"  {len(FLOWS)} flows, {len(conn_refs)} connection references, "
          f"{len(env_vars)} environment variables")
    print("  NO canvas app, and no placeholder for one. See CANVAS_APP_ASSEMBLY.md.")


if __name__ == "__main__":
    main()
