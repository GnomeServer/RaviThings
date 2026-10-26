# Typed questions for the Chalk Line intake pile

This is a fictional class desk. Answering these questions dispatches nothing and releases nothing.

Read these two files with the course_read tool, passing each path as the path argument, before you answer:

- out/state.json
- shared/controls/questions.json

The state file holds the catalog, the desk rules in short form, and forty messages. Each message carries an `id`, a `time`, a `from` line, the `text`, and a list of quantity `candidates` that software already found in the text. Each candidate has an `id` such as `q1` and the `text` it covers.

Answer every question in the question file for every message, in the order the messages appear, including the eighth question at the end of the file, which you answer under its own key the same way as the other yes-or-no questions. Use only the options each question lists. For the `quantity` question the options are that message's candidate IDs plus `NONE`. For the `replaces` question the options are the IDs of messages that appear earlier in the state file plus `NONE`.

Reply with exactly one JSON document and nothing else, in this shape:

{"schema": "chalk-line/answers/1", "answers": [{"id": "CL-001", "request": {"p": 0.0}, "line": {"choice": "NONE", "confidence": 0.0}, "quantity": {"choice": "NONE", "confidence": 0.0}, "urgency": {"score": 0, "confidence": 0.0}, "authority": {"p": 0.0}, "instructs_desk": {"p": 0.0}, "replaces": {"choice": "NONE", "confidence": 0.0}, "<key of the eighth question>": {"p": 0.0}}]}

The example values are placeholders. Replace them with your answers. Keep exactly these keys for every message. Numbers are decimals from 0 to 1; a score is an integer level index. Do not add commentary, do not wrap the document in a code fence, and do not write any file.
