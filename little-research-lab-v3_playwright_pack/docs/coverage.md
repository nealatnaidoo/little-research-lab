# Coverage Map (initial)

> This is an initial scaffold. As UI selectors and seeding/cleanup are finalized, expand the regression suite until TA coverage is complete.

| Epic/Story | TA IDs | Flow | Test file | Test name(s) | Tags |
|---|---|---|---|---|---|
| E1.1 | TA-0001, TA-0002 | Admin Settings load/save | tests/admin/settings.spec.ts | [E1.1+TA-0001] settings load/save | @smoke @regression |
| E2.2 | TA-0009, TA-0011 | Asset upload + list | tests/admin/assets.spec.ts | [E2.2+TA-0009] upload asset | @smoke @regression |
| E7.1 | TA-0043 | Create internal redirect + 301 | tests/admin/redirects.spec.ts, tests/public/redirects_public.spec.ts | [E7.1+TA-0043] create redirect / verify 301 | @smoke @regression |
| E8.1 | TA-0049 | Audit log records admin actions | tests/admin/audit.spec.ts | [E8.1+TA-0049] audit entry exists | @smoke @regression |
| R1 | (various) | Draft/scheduled not public | tests/public/visibility_guard.spec.ts | [R1] draft not accessible (TODO) | @regression |
| E5.* / R3 | TA-0026..0033 | Scheduling invariants | tests/admin/schedule.spec.ts | (TODO skeleton) | @regression |
| E6.* / R4 | TA-0034..0042 | Analytics privacy | tests/admin/analytics.spec.ts | (TODO skeleton) | @regression |

