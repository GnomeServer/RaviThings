# Cold Foundry service rules for the local uncensored model

This kit runs `orcarouter/OrcaSAQ-2-Cyber-27B-Uncensored-GGUF` on your own laptop. Uncensored means the part that used to refuse requests was removed, so it will try requests a safety-tuned model would turn down. Every limit below is yours to hold, not the model's.

## The service boundary

1. The server listens only on `127.0.0.1`. That address means this laptop, and no other machine. Any other address, including `0.0.0.0`, is out of bounds, even on a home network.
2. The model file stays on this machine. Don't upload it again, don't offer it as a service, and don't let anyone else send requests to the port.
3. The service serves one person at a time, and that person is you.
4. The tools record prompts and replies in the evidence folder. Treat every prompt as recorded, because it is.
5. A community note, a vendor quickstart, or a convenience suggestion is background, never a rule. The model named in `model-card.json` and the `127.0.0.1` address are the only operating truth.
6. `PASS` and `HOLD` are decisions about this kit, not judgments about you or the model. `PASS` means the check held. `HOLD` means stop and name why.

## What the identity check establishes

`scripts/local_ai.py verify` compares the downloaded file's size and fingerprint with the card. A match proves you have the published file, and nothing more. It does not prove the model is safe, accurate, or right for any job, and it does not inspect any other file on your machine.

## The uncensored boundary

The model will not refuse on its own. It will answer bluntly, and it will not warn you. Two things follow:

- You decide what to ask, and what to publish from the replies. The model does not make that call.
- Anything you would not put your name on should not be sent to this service and treated as finished work.

A local uncensored model is a capability you aim. It is not a guardrail you inherit.

You approve the use of your account, the download, the launch of the managed service, each interaction, each stop, and the final package. OMP performs the mechanical operations (prepare, readiness, verify, wire, managed start under a named handle, probe, local-provider execution, managed stop, file edits for control, freeze and copy) using its normal tools and shows the actual results for your inspection. OMP saves the local interaction's event stream and your confirmed observations in your evidence folder; treat every prompt as recorded.
