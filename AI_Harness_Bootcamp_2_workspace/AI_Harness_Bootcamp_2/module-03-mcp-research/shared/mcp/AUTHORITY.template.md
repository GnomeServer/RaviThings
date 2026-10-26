# Connection authority

This file states what the connection to the vault may do. Write it before you connect the server, then change the server's settings in `mcp.json` so they say exactly the same thing. The probe and the launcher refuse a connection when the two files disagree.

Take tool names from the inspector's table. A tool you leave out of `allow_tools` is hidden from the model.

| Field | Meaning |
|---|---|
| `phase` | `research`, `partner`, or `revoked`. Each live run is bound to one phase. |
| `allow_tools` | The tools the model may call. |
| `read_scope` | Folders the connection may read. Write each as a folder path ending in a slash, such as `"Handbook/"`. |
| `write_scope` | Folders the connection may change. They must be inside `Drafts/`. Use `[]` when nothing should be written. |
| `create_only` | `true` means a note that already exists can never be changed or removed. Only new notes can be created. |

Each field has a matching setting in the server's `args` in `mcp.json`.

| In this file | In `mcp.json` `args` |
|---|---|
| each folder in `read_scope` | `"--read-prefix", "Folder/"` |
| each folder in `write_scope` | `"--write-prefix", "Folder/"` |
| `create_only` is `true` | `"--no-overwrite"` |
| `write_scope` is `[]` | `"--read-only"` |

## Declaration

```json
{
  "schema_version": 1,
  "phase": "research",
  "allow_tools": [],
  "read_scope": [],
  "write_scope": [],
  "create_only": false
}
```
