# Module 10 · Stand up and package a local uncensored AI

You open ordinary Oh My Pi and copy the prompts in the lab. OMP performs the mechanical steps with its normal tools. You inspect the returned evidence, authorize downloads, launches and stops, and decide what to keep. The model is `orcarouter/OrcaSAQ-2-Cyber-27B-Uncensored-GGUF`, one file of about 15.7 GB. Uncensored means the part that used to refuse requests was removed. It will answer bluntly, and it will not warn you or decide what should go out. You hold that line. The server listens only on `127.0.0.1`, which means only this laptop can reach it. The model file stays on this laptop. The tools record what you ask and what it answers.

Plan for about three hours on Thursday. That is a rough estimate. You work on your own laptop and finish in this session, including shutdown. If access, hardware, or time stops a required step, write the reason for `HOLD` and close the attempt before the session ends. `HOLD` means the work stopped for a named reason. It is not a grade.

## Start here

Ask staff for the approved `hf` and `llama-server` executable paths, then [check local-model readiness](shared/MODULE_10_LAB.md#check-local-model-readiness-before-downloading) before downloading or launching. Keep existing installations. A preflight reports capacity and prerequisites without downloading or starting a service; each machine still needs a complete exact-model rehearsal.

1. [Stand the model up and keep the files](shared/MODULE_10_LAB.md) by copying prompts into ordinary OMP.
2. Read the [service rules](shared/case/SERVICE_RULES.md) before you start the server.
3. After your own run is done, freeze the eleven files in the [package](shared/PACKAGE.md) and copy them. Check that copy from a new terminal and a new OMP conversation. Do not copy the model file again, and do not download it again.

The copy has only the eleven files the package names: the instructions, the check scripts, the case and rules, the on/off control, and the saved baseline. Leave the model file where you downloaded it. Evidence, including the stop receipt, and the chat stay outside the copy. The fresh-copy check reads the named sections and confirms the named files are in the folder. It does not carry out the instructions, and it does not start the server again.
## Keep it on this laptop

Start the server only on `127.0.0.1`. Keep the model file on this laptop, under your own account. Don't upload it again, don't share the address, and don't let anyone else send requests to it. The tools record prompts and replies in your evidence folder. What you produce is for class use only. This is a local service you can run yourself. Finishing the run does not authorize anything beyond the evidence you saved.
