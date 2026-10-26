# Module 8 · Control hallucinations

You already have Oh My Pi, an OpenRouter key, and the TypeSafe skill. Check a brief that sounds ready to send, two ways. First, code and Jev test every claim against its own packet: find the value in the record, ask whether the record supports the sentence, ask how likely the claim is wrong and escalate only the flagged ones, and ask whether the packet holds the answer at all. Then run five sessions on the same brief. Two reviewers look separately. A third rewrites the claims. The same two look again, without their old answers. You decide which claims the sources support. A typed answer is a check. A clean JSON file is not a true brief. Allow about three hours. [Open the lab](shared/MODULE_08_LAB.md).

You copy each step's prompt into your ordinary Oh My Pi (OMP) conversation. That conversation is the **coordinator**: it writes and runs the Jev check code, runs the supplied helper, and shows you the files it made. The Jev calls go to `jev-1.13` through OpenRouter with the key you already have; they are not audited child calls. Each of the five audited child calls, the two reviews, the correction and the two fresh reviews, runs as a separate child session. A child sees only its own frozen inputs, never your notes, your check files, or the chat.

## Slope Brief

Slope Brief concerns heater-fuel cans at Ridge Depot for Clinic T-8 on vehicle `SB-4`. The brief has seven claims across three packets, PC-01, PC-02, and PC-03. Do not mix their masses or clocks. The brief says the shipment is released. The sources do not. The brief does not dispatch the vehicle.
