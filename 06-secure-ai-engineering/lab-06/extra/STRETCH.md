# Lab 6 - Stretch challenges

Each keeps the "one model, generated artifacts, every control evidenced" discipline.

1. **Add a component and a flow.** Suppose the agent gains a `notify_slack` tool. Add it to
   `system_model.py` (a new flow crossing to "external"), re-run `threat_model.py`, and watch a
   new exfiltration threat appear. Add a control for it in `controls.py` with an evidence test,
   or mark it Accepted with a rationale. The tests must stay green.

2. **Map to your own framework.** Replace the example clause ids in `controls.py` with your
   organisation's control catalogue (or add a new framework to `compliance.py`). Re-run
   `compliance.py` and `build_docs.py`.

3. **Fail the traceability on purpose.** Remove an `evidence` entry from one control and run
   `python -m pytest`. See which test catches it. This is the guardrail that stops the document
   shipping with an unproven claim.

4. **Add a residual-risk register.** Extend `build_docs.py` section 9 to list every
   Not-applicable / Accepted item in a table with owner and review date.

5. **Wire live evidence into CI.** Make `link_lab5.py` exit non-zero if any cited test is missing
   from the Lab 5 run, so a broken control fails the build.
