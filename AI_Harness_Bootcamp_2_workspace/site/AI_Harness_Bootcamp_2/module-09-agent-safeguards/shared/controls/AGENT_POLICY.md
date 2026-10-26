# Agent policy

This file is the class policy for one Night Desk turn. Freeze it before the first agent command. The JSON block is the declaration the launcher reads. The sentences around it explain the fields. Do not add keys, and do not turn a false value into true.

A saved policy is the allow-list you freeze before a turn. Yolo off means the agent does not get a blanket approval to act. The read root is the work folder. The write root is the `artifacts` folder inside that work folder. The tools list is the only tool names the turn may use. Skills off means no skill install. Gateway off means no messaging gateway.

```json
{
  "schema_version": 1,
  "yolo": false,
  "read_root": ".",
  "write_root": "artifacts",
  "tools": ["course_read", "course_write"],
  "skills": false,
  "gateway": false
}
```
