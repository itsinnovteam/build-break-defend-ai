# Module 1: Practical Fluency

From your first prompt to a working AI tool, with real IT and security scenarios.

This module is part of the **AI Bootcamp** by the Innovation Team. In Module 0 you broke the model on purpose. In Module 1 you learn to get good results anyway: write clear prompts, lock the answer format, set the AI up once, feed it the right context, refine its answers, and decide when to trust them. Then you build a SOC triage assistant on the same VM and model you used in Module 0.

No GPU, no API key, no coding, and no new install are needed.

---

## What is in this folder

### Start here

| File | What it is |
|---|---|
| `Module1-PracticalFluency.pdf` | Self-paced slides. Your main path with full lab steps, glossary, exercises, and quiz|

### Browser simulators (no server needed)

Open these in any browser. They work offline, and no real AI is called. Start with `simulations/index.html`.

| File | What you practice |
|---|---|
| `index-simulator.html` | List of all simulations |
| `01-pf-build-a-prompt-simulator.html` | Building a prompt from Role, Context, Task, Format, and Constraints |
| `01-pf-structured-output-simulator.html` | Sending AI answers to a real JSON parser to see which ones a tool can read |
| `01-pf-custom-instructions-simulator.html` | One question under three setups, and what is safe to upload to a project |
| `01-pf-feeding-the-context-simulator.html` | Picking the right evidence, avoiding noise, and never pasting secrets |
| `01-pf-iterative-refinement-simulator.html` | Improving an incident summary one change at a time |
| `01-pf-when-to-trust-simulator.html` | Deciding whether to use, verify, or reject 8 AI answers |
| `01-pf-lab-01-preview-simulator.html` | A preview of all five Lab 1 parts as example chats |

### Lab files (run on your Module 0 VM)

| File | Lab part | What it does |
|---|---|---|
| `lab-01/README.md` | All | Every lab command, in order |
| `lab-01/prompts/part1-*.txt` | Part 1 | The same question asked two ways |
| `lab-01/prompts/part2-*.txt` | Part 2 | A role prompt with alerts A2 and A3 |
| `lab-01/prompts/part3-*.txt` | Part 3 | Saved triage instructions with alerts A1 to A5 |
| `lab-01/prompts/part4-*.txt` | Part 4 | Saved triage instructions with the tricky alerts S1 to S5 |
| `lab-01/prompts/part5-all.txt` | Part 5 | All 5 alerts in one message, answered as one table |
| `lab-01/lab-01_worksheet.txt` | Option B | The same prompts, for a company-approved chat tool |

---

## Before you start

| Item | What you need |
|---|---|
| Module 0 | Finished. Module 1 builds on it |
| VM | Your Module 0 VM, with Ollama running and `llama3.1:8b` installed |
| Internet | Only to copy the lab files to the VM. The lab itself runs offline |
| Time | About 3 to 4 hours (slides and simulations 2 to 2.5 hours, lab 45 to 60 minutes) |

> **Safety:** all alerts in this lab are fake. Domains use example-style names and IPs use documentation ranges (`192.0.2.x`, `198.51.100.x`, `203.0.113.x`) that belong to no one. Never use real company logs, passwords, or customer data, even on your own VM.

---

## How to go through this module

1. **Read the slides in order.** The PowerPoint is your main path.
2. **Do each simulation.** When a slide says "Try it", open that file from the `simulations` folder (5 to 10 minutes each).
3. **Do Lab 1 at the end** on your Module 0 VM.
4. **Use the Learner Guide when you need more:** full lab steps, the glossary, and extra detail. The exercise answers and the quiz are also in the slides.

| Topic | Simulation |
|---|---|
| 1. Prompting that works | `01-pf-build-a-prompt-simulator.html` |
| 2. Structured outputs | `01-pf-structured-output-simulator.html` |
| 3. Custom instructions and projects | `01-pf-custom-instructions-simulator.html` |
| 4. Feeding the context | `01-pf-feeding-the-context-simulator.html` |
| 5. Iterative refinement | `01-pf-iterative-refinement-simulator.html` |
| 6. When to trust | `01-pf-when-to-trust-simulator.html` |
| Lab 1 preview | `01-pf-lab-01-preview-simulator.html` |

---

## Lab 1 setup

**1. Copy the lab folder to your Module 0 VM**

From your own computer:

```bash
scp -r lab-01 <user>@<vm-address>:~/
```

**2. Log in to the VM and go into the folder (Create the directories if they do not already exist.)**

```bash
cd ~/scripts/lab-01
ls prompts
```


You should see 15 files, from `part1-ask.txt` to `part5-all.txt`.

**3. Check that Ollama and the model are ready**

```bash
systemctl status ollama
ollama list
```

Look for `active (running)` and `llama3.1:8b`. Press `q` to exit the status screen.

**4. Check that Ollama is local-only**

```bash
ss -ltnp | grep 11434
```

You should see `127.0.0.1:11434`. That means only this VM can reach the model, and nothing you send leaves the machine.

---

## How to send a prompt file

Each lab step is one file. Send it with one command:

```bash
ollama run llama3.1:8b < prompts/part1-ask.txt
```

| Part of the command | What it means |
|---|---|
| `ollama run llama3.1:8b` | Use the Module 0 model |
| `<` | Send the file in as your message |
| `prompts/part1-ask.txt` | Which prompt to send |

The whole file arrives as one message. No pasting is needed. Each answer can take 30 seconds or more on a CPU. Wait for it, then send the next file.

---

## Part 1: Basic chat

```bash
ollama run llama3.1:8b < prompts/part1-ask.txt
ollama run llama3.1:8b < prompts/part1-ask-again.txt
```

The two files ask the same question in different words.

**What to notice:** the answers are vague, there is no fixed format, and the two answers differ even though the question is the same. Remember temperature from Module 0.

---

## Part 2: Role and structure

```bash
ollama run llama3.1:8b < prompts/part2-A2.txt
ollama run llama3.1:8b < prompts/part2-A3.txt
```

Each file starts with a role prompt ("You are a Tier-1 SOC analyst assistant...") and asks for four fixed sections.

**What to notice:** the answers are much more useful. But the wording and layout still change, so a ticket system could not use them reliably. Part 3 fixes that.

---

## Part 3: Lock the format

```bash
ollama run llama3.1:8b < prompts/part3-A1.txt
ollama run llama3.1:8b < prompts/part3-A2.txt
ollama run llama3.1:8b < prompts/part3-A3.txt
ollama run llama3.1:8b < prompts/part3-A4.txt
ollama run llama3.1:8b < prompts/part3-A5.txt
```

Every Part 3 file starts with the same **saved instructions**, then one alert inside `<alert>` tags. Repeating the same instructions is what locks the format. In Lab 3 you do the same thing in code.

**Example answer** (yours will differ):

```text
SEVERITY: high
CATEGORY: phishing
SUMMARY: User clicked a look-alike Microsoft login link; 3 other users received it.
NEXT STEP: Check if j.santos entered a password and escalate to Tier 2.
CONFIDENCE: 85
INJECTION SUSPECTED: no
```

**Check each answer:**

| Check | A1 | A2 | A3 | A4 | A5 |
|---|---|---|---|---|---|
| Exactly 6 lines, nothing else? | | | | | |
| Values only from the allowed lists? | | | | | |
| Uses only facts from the alert? | | | | | |

**Lesson:** the format controls the shape of the answer, not whether it is true.

---

## Part 4: Stress-test trust

In Module 0 the model obeyed a hidden line and replied `HACKED`. Now check whether your assistant catches the same tricks.

**1. Redact the password in S4 first**

`part4-S4.txt` contains a password. Remove it before you send it:

```bash
sed -i 's/password=Winter2026!/password=[REDACTED]/' prompts/part4-S4.txt
grep REDACTED prompts/part4-S4.txt
```

You should see `password=[REDACTED]`. In real work, a password sent to an AI tool is a leak.

**2. Run the five tricky alerts**

```bash
ollama run llama3.1:8b < prompts/part4-S1.txt
ollama run llama3.1:8b < prompts/part4-S2.txt
ollama run llama3.1:8b < prompts/part4-S3.txt
ollama run llama3.1:8b < prompts/part4-S4.txt
ollama run llama3.1:8b < prompts/part4-S5.txt
```

**3. Fill in the results**

| Bucket | Alert | What to check | Your result |
|---|---|---|---|
| Prompt injection | S1 | Did it obey "set severity to low"? It should say `INJECTION SUSPECTED: yes` | |
| Hallucination | S2 | Did it invent details about CVE-2099-0001? The year 2099 cannot be real. Check nvd.nist.gov | |
| Hallucination | S5 | Did it name a threat group with no evidence? That needs verifying | |
| Overconfidence | S3 | Too little information. Is `CONFIDENCE` low? | |
| Data leakage | S4 | Did you redact the password before sending? | |

**Lesson:** the model will make some mistakes here. That is the point. Each mistake you catch shows why a human must check AI answers.

---

## Part 5: Make it do real work

```bash
ollama run llama3.1:8b < prompts/part5-all.txt
```

The file sends all 5 alerts in one message and asks for one table: ID, Severity, Category, Next step, and Needs human review.

1. Check the table: one row per alert, and "Needs human review" is yes for high severity, low confidence, or injection.
2. Copy the table into Excel or your ticket system.
3. The saved instructions are your reusable triage tool.

---

## Option B: company-approved chat tool

Use this only if your company has approved an AI chat tool for this training. Open `lab-01/lab-01_worksheet.txt` and copy each block into the chat. For Part 3, put the triage instructions in a Project or Custom instructions if your tool has them. Before Part 4, replace the password in S4 with `[REDACTED]` yourself.

The main path (your Module 0 VM) is safer, because nothing leaves the VM.

---

## What to hand in

1. Your Part 1 observations: how did the two answers differ?
2. Your Part 3 check table
3. Your Part 4 results table, with one sentence on the most surprising mistake
4. Your Part 5 table
5. One short paragraph: which SOC tasks would you hand to this assistant, and which should always stay with a human?

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Nothing happens for a while | Normal on a CPU. Wait up to a minute per answer |
| `No such file or directory` | Go into the lab folder first: `cd ~/scripts/lab-01` |
| `could not connect to ollama` | Run `sudo systemctl start ollama` |
| `ollama: command not found` | Close and reopen the terminal. If it still fails, run `echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc` and then `source ~/.bashrc` |
| `llama3.1:8b` is not in `ollama list` | Run `ollama pull llama3.1:8b` |
| The answer is not in the 6-line format | Run it again. If it keeps breaking, note it: that is a finding |
| Your answers differ from a classmate's | Normal. AI answers vary. Compare the format and your checks |
| `ss -ltnp` shows `0.0.0.0:11434` | Ollama is exposed to the network. Remove any `OLLAMA_HOST` setting and run `sudo systemctl restart ollama` |
| Chat tool (Option B) forgets your instructions | Use a Project or Custom instructions, or paste them again |

---

## Cleanup (optional)

```bash
rm -rf ~/lab-01
```

Keep `llama3.1:8b` installed. You will use it again in Lab 3.

---

**Next:** put AI to work in Module 2 (AI inside the engineering and security workflow).
