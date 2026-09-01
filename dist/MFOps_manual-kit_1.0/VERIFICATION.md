# VERIFICATION — sign this before any CSV touches any list

**Loading configuration before this gate is signed is forbidden.** An index missed here is found now, while every list is empty and every index is still cheap to create.

| # | List | Columns expected | Columns found | Indexes expected | Indexes found | PASS |
|---|---|---:|---|---:|---|---|
| 01 | `MF App Config` | 6 |    | 2 |    |    |
| 02 | `MF Feature Flags` | 7 |    | 1 |    |    |
| 03 | `MF Installation` | 18 |    | 4 |    |    |
| 04 | `MF Facility` | 19 |    | 5 |    |    |
| 05 | `MF EOM Requirement` | 23 |    | 4 |    |    |
| 06 | `MF Document Destination` | 15 |    | 3 |    |    |
| 07 | `MF Non Duty Day` | 6 |    | 4 |    |    |
| 08 | `MF Notification Rule` | 9 |    | 3 |    |    |
| 09 | `MF Security Mapping` | 20 |    | 8 |    |    |
| 10 | `MF Access Request` | 11 |    | 4 |    |    |
| 11 | `MF Calendar Event` | 13 |    | 4 |    |    |
| 12 | `MF EOM Item` | 32 |    | 13 |    |    |
| 13 | `MF EOM Submission` | 33 |    | 13 |    |    |
| 14 | `MF Unmatched File` | 13 |    | 4 |    |    |
| 15 | `MF EOM Status` | 39 |    | 8 |    |    |
| 16 | `MF EOM Audit` | 9 |    | 4 |    |    |
| 17 | `MF App Event Log` | 13 |    | 6 |    |    |
| | **TOTAL** | **286** | | **90** | | |

The six lists that will grow past 5,000 rows, where a missing index hurts most:

- [ ] `MF_EOM_Item`: **13** indexes
- [ ] `MF_EOM_Submission`: **13** indexes
- [ ] `MF_EOM_Status`: **8** indexes
- [ ] `MF_Security_Mapping`: **8** indexes
- [ ] `MF_App_Event_Log`: **6** indexes
- [ ] `MF_EOM_Audit`: **4** indexes

```
SAFE TO LOAD CONFIGURATION:  YES / NO
Signed:                      ____________  Date: ______
```

YES only when every row above reads PASS. Row-level behaviour in the tenant (throttling, threshold behaviour at 5,000+) is NOT TESTABLE LOCALLY and is not claimed here.
