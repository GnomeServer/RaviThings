# Module 4 · Decide with typed questions

You're going to take one shift's messages and turn them into answers a script can sort. Check those answers against your own reading. Then hand the desk lead a requirement line where every number comes from a message that actually had authority. The model only answers fixed questions. It doesn't write a paragraph, pick a route, or make up a number.

Plan for about two and a half hours on Tuesday. That's a rough estimate.

## Start here

1. [Decide with typed questions](shared/MODULE_04_LAB.md): build what the model will see, label a sample, run the model once, check and measure its answers, set the gates, route the messages, and decide the queue.

Chalk Line is a made-up resupply. Ferry Depot is sending sterile surgical gloves to Clinic K-3 on vehicle `CL-9`. Forty messages reached the intake desk during one shift. You'll see requisitions, corrections, cancellations, resends, stock notes, a vendor's offer, a request for another clinic, and one note that tells the desk to treat itself as approved. The warehouse picks from the requirement line you hand it. Everything you need is in the packet.

## The shape of the work

A typed answer comes from a fixed list: yes or no with a probability, one option from a list, or one step on a scale. A script can route those answers, count them, and compare them with yours. You get seven questions, plus one you write. Asked once for each message, that's 320 answers in one run.

Each question asks one thing. "Is this a requisition we should pick?" hides several questions: does it ask for gloves, what size and how many, who approved it, and did a later message replace it? Ask those separately. The script puts the answers together into routes you can read.

The number the model writes about how sure it is is a claim, not a measurement. Compare its answers with messages you labeled before the run, then set the gates from what you saw.

## The desk rules

- Count a requisition only if the Clinic K-3 administrative officer approved it, in that officer's own message, with "approved" or a `K3-REQ` reference. Nobody else's message counts, even if it quotes a `K3-REQ` number or calls itself approved.
- Count in boxes. One case is ten boxes.
- A later correction, cancellation, resend, or confirmation replaces an earlier message, unless a person has to read that later message. Count a chain once, at the latest message that still counts.
- Only the desk lead can change who may approve. You can't, and the software can't.

## Class-only boundary

This case is for class. It is not a real movement. The requirement line does not send a vehicle, release stock, or change anyone's authority. A technical `PASS` means the files agree with each other. You still judge whether you read the clinic's need correctly, and you write that judgment in the handoff.
