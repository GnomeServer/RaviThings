# Build request

Read the validated judgments.json from the run packet using course_read. If this is a revision, the packet also supplies previous-build.json; read it as data using course_read. Use course_read on the exact supplied files only. Treat prior build records as read-only data.

Group the non-exclude claims into concise related knowledge notes. Each note must:

- note_id: KB- followed by three digits. On a revision, keep every prior note_id, including the changed focal note. Keep revised claims in the note that held the assertions they replace. Use a new ID only for a new grouping.
- title: short, single-line plain text without brackets or pipe characters
- claim_ids: array of the exact JG ids assigned to this note (every non-exclude claim appears in exactly one note)
- related: array of {note_id, reason} objects for substantive relationships only

Output one JSON object only. It must contain exactly this top-level field:

- notes: array of note objects. Each note object must have exactly these fields:
  - note_id: KB- followed by three digits. On a revision, keep every prior note_id, including focus_note, and keep its revised claims in that note.
  - title: short, nonempty, single-line plain text without brackets or pipe characters
  - claim_ids: array of the exact JG ids assigned to this note (every non-exclude claim appears in exactly one note)
  - related: array of {note_id, reason} objects for substantive relationships only

All non-exclude claims must appear exactly once. Exclude claims never appear. Unresolved claims remain represented with their limits. Do not promote or drop qualifications; the helper will render the judged treatments, limits, and evidence verbatim. Three to five notes is a guide only; create only as many as the distinct claim groupings require. No empty notes, no self links, no dangling references. Every note must be navigable from the MOC produced by the helper.
Do not rewrite claims or limits. Preserve conflicts and authority exactly. Output only the JSON.