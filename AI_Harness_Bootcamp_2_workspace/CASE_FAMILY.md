# Case family

Fictional, class-only. Not a real movement, dispatch, or operations order.

## Supported missions

Each module owns one movement. The movements are named in [MISSION_THREAD_SCENARIOS.md](MISSION_THREAD_SCENARIOS.md). Module 01's movement is Operation Cold Lantern: usable medicine kits from Red Mesa Depot to Clinic H-17 over Route R-71 by 16:00 MDT on 6 October 2026. No other module uses that movement, those proper names, or Monday afternoon's calculated results.

## Stake

Whether that module's handoff is supported. A locally true step cannot rescue a broken handoff.

## Surface path

These owners belong to Module 01 only. Other modules do not reuse `MO-27`, `VX-204`, `PR-4418`, `R-71`, or Clinic H-17.

System, then owner:

1. Requirement — North Basin Mission Control (`MO-27`)
2. Warehouse custody — Red Mesa WMS
3. Quality release — North Basin Quality Office
4. Vehicle / payload — Fleet Engineering (`VX-204`)
5. Movement authority — Movement Registry (`PR-4418`)
6. Route / gate — Road Authority (`R-71`)
7. Delivery / receiving — Clinic H-17
8. Usable effect — clinic receipt (not yet occurred at 14:05 MDT)

## Adapter rules

- Each adapter supplies one self-contained case for the movement named for that module in [MISSION_THREAD_SCENARIOS.md](MISSION_THREAD_SCENARIOS.md). It does not import another module's movement, verdict, or case identifiers.
- A module gate does not consume another module’s product.
- Learner-facing files never contain `246 kg`, `1,404 kg`, or `3 minutes late`, except Module 01 staff, reference, and calculator paths already allowed to carry those tokens.
- No module teaches cyber mission-thread defense or real dispatch.
- New packets follow [MISSION_THREAD_SCENARIOS.md](MISSION_THREAD_SCENARIOS.md). Replacement specs for Modules 02–10 are adopted in the shipped labs; retired thin-adapter inputs are not active work.

## Real-software exception

Module 10 runs real software instead of a fictional logistics movement. Its independence rule is unchanged: it supplies its own case and does not import another module's product or identifiers. Its safety rule is the bounded-use rule that governs the pinned model: the service binds loopback only, the weights stay on the learner's machine and are never re-uploaded or served to another person, and guardrails belong to the operator because the model's refusal direction was removed. The other ten sessions keep the fictional, class-only boundary above.
