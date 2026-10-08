# Lab 2 – Prompts

Two ways to send these prompts (the same two paths as Lab 1):

| | Main path: your Module 0 VM | Option B: approved chat tool |
|---|---|---|
| Model | llama3.1:8b, running locally | Your company-approved AI chat tool |
| Data | Nothing leaves the VM (safest) | Sent to the provider under your company's contract |
| How | One command per prompt file in `prompts/` | Copy the text of the prompt file into the chat |

Main path example (from inside the lab2 folder):

    ollama run llama3.1:8b < prompts/p1_security_review.txt

Each answer can take 30 seconds or more on a CPU. That is normal.

Before you send anything:
- This lab contains **no real data**: the token is fake and all IPs are
  documentation-only ranges (192.0.2.x, 198.51.100.x, 203.0.113.x).
- At work, follow the Module 1 safety rules: never paste secrets, mask personal
  data, use approved tools only.

---

## P1 – AI security review (Part 4) → `prompts/p1_security_review.txt`

Already filled in with the SPEC and the full triage_tool.py, wrapped in
`<spec>` and `<code>` tags (Module 1: separate data from instructions).

## P2 – Fix ONE rule (Part 5) → `prompts/p2_fix_R1.txt` … `p2_fix_R7.txt`

One file per rule, already filled in with that rule and the original function.
Template, if you need to write your own:

```
Fix ONLY SPEC rule <R#> in the function below.
Rules: keep the function name and parameters exactly the same,
use only the Python standard library, do not use a shell,
do not hardcode secrets. Show the full corrected function,
then explain the change in 2 sentences.

<rule>
<paste that one row from SPEC.md>
</rule>

<function>
<paste only that function>
</function>
```

## P3 – Write tests for ONE rule (Part 5) → `prompts/p3_tests_R1.txt` … `p3_tests_R7.txt`

Template:

```
Write pytest tests for SPEC rule <R#> of triage_tool.py.
Requirements: name every test test_r<#>_<something>,
include boundary values and at least one malicious input,
each test must FAIL if the rule is broken,
use tmp_path for files and monkeypatch for environment variables,
no network, no real data. Put any sample log lines directly
inside the test file. Import <function> from triage_tool.
Show only the Python code.

<rule>
<paste that one row from SPEC.md>
</rule>
```

## P4 – Close a gap found by the meta-test (Part 6)

This one needs your own test, so write it yourself (save it as a .txt file in
prompts/ if you use the main path):

```
My meta-test reports this bug was MISSED by my tests:
<paste the MISSED line>
Here is my current test for that rule:
<test>
<paste the test>
</test>
Write ONE additional pytest test that would FAIL on that bug and PASS on
correct code. Explain in one sentence why my current test missed it.
```
