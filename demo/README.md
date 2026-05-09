# WorkflowPatch Demo Source

This public demo is deliberately small:

`mock-input.csv -> process_demo.py -> review-queue.csv + error-log.csv`

It demonstrates the operating pattern behind a WorkflowPatch sprint:

- validate required fields before processing;
- block duplicate request ids;
- route unsafe rows to a visible error log;
- keep external/customer-facing text in a human approval queue;
- produce outputs that a non-technical operator can inspect.

Run locally:

```bash
python3 process_demo.py
```

Expected output:

```text
review_rows=4
error_rows=2
```
