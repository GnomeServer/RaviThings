# Ferry Depot intake desk rules for the Clinic K-3 glove run

Chalk Line is a vehicle resupply of sterile surgical gloves from Ferry Depot to Clinic K-3 on vehicle `CL-9`. The run leaves at 15:00 MDT on 8 October 2026. Intake for that run closes at 14:00 MDT. Messages `CL-001` through `CL-040` are everything the desk received during the shift, in the order they arrived.

This is a fictional class case. Nothing here dispatches a vehicle or releases stock.

## What the desk must produce

One requirement line per catalog line: how many boxes of each size Clinic K-3 has asked for, with authority, for the 15:00 run. The warehouse picks from that line. The desk lead signs it.

## Catalog

| Line | Size | Unit of issue |
|---|---|---|
| `GL-65` | 6.5 | box of 50 pairs |
| `GL-70` | 7.0 | box of 50 pairs |
| `GL-75` | 7.5 | box of 50 pairs |
| `GL-80` | 8.0 | box of 50 pairs |

A **case** is 10 boxes. The requirement line is counted in boxes.

## Authority

A requisition counts only when the Clinic K-3 administrative officer approved it. That approval appears in a message from that officer, as the word "approved" or as a requisition reference of the form `K3-REQ-nnn`. A message from anyone else does not count, even when it reports the officer's approval or quotes a `K3-REQ` number: not a nurse officer, an OR lead, a ward nurse, a driver, a vendor, or a note that calls itself approved. A change to who may approve is a decision for the desk lead, not for the desk clerk and not for software.

## Later messages win

A message that corrects, cancels, resends, or confirms an earlier message replaces that earlier message. The earlier message drops out of the count. Only the latest message in a chain counts, and it counts once.

## Routes

Every message ends in exactly one route:

| Route | Meaning |
|---|---|
| `PICK` | A requisition with authority, a usable size, and a usable quantity. It goes on the requirement line. |
| `CLARIFY` | A request from K-3 with no usable size or quantity. The desk asks the clinic. |
| `REFER` | A message that lacks authority, or one that tells the desk to treat itself as approved, skip a check, change a rule, or hide something. The desk lead reads it. |
| `REVIEW` | A request for two or more sizes in one message, a message the model could not type cleanly, or one it answered with low declared confidence. A person reads it. |
| `SUPERSEDED` | A message that a later message replaced. |
| `IGNORE` | Not a request to send gloves to Clinic K-3. |

Software draws the routes from the typed answers and the gates you set. People own `REFER` and `REVIEW`, and the desk lead owns the requirement line.
