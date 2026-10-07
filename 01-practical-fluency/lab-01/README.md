# LAB 1 - FROM CHAT TO TOOL

## Main Path: Your Module 0 VM

> **Recommended:** Use your Module 0 VM. This is the safest option because nothing leaves the VM.

### 1. Create and enter the lab directory

```bash
cd scripts

mkdir -p lab-01

cd lab-01
```

### 2. Check that the model is available

```bash
ollama list
```

You should see:

```text
llama3.1:8b
```

### 3. Run one prompt file at a time

Each prompt file represents one message.

Run one command, wait for the model to finish responding, then continue to the next command.

---

## Part 1 - Basic Chat

```bash
ollama run llama3.1:8b < prompts/part1-ask.txt
```

```bash
ollama run llama3.1:8b < prompts/part1-ask-again.txt
```

---

## Part 2 - Role and Structure

```bash
ollama run llama3.1:8b < prompts/part2-A2.txt
```

```bash
ollama run llama3.1:8b < prompts/part2-A3.txt
```

---

## Part 3 - Lock the Format

Each prompt file starts with the same saved instructions to keep the output format consistent.

```bash
ollama run llama3.1:8b < prompts/part3-A1.txt
```

```bash
ollama run llama3.1:8b < prompts/part3-A2.txt
```

```bash
ollama run llama3.1:8b < prompts/part3-A3.txt
```

```bash
ollama run llama3.1:8b < prompts/part3-A4.txt
```

```bash
ollama run llama3.1:8b < prompts/part3-A5.txt
```

---

## Part 4 - Stress-Test Trust

### Important: Stop before running S4

The `part4-S4.txt` file contains a sample password.

Redact it first:

```bash
sed -i 's/password=Winter2026!/password=[REDACTED]/' prompts/part4-S4.txt
```

Verify that the password was replaced:

```bash
grep REDACTED prompts/part4-S4.txt
```

You should see:

```text
[REDACTED]
```

Once verified, run the prompts one at a time:

```bash
ollama run llama3.1:8b < prompts/part4-S1.txt
```

```bash
ollama run llama3.1:8b < prompts/part4-S2.txt
```

```bash
ollama run llama3.1:8b < prompts/part4-S3.txt
```

```bash
ollama run llama3.1:8b < prompts/part4-S4.txt
```

```bash
ollama run llama3.1:8b < prompts/part4-S5.txt
```

---

## Part 5 - Real Work

Process all five alerts and produce one table:

```bash
ollama run llama3.1:8b < prompts/part5-all.txt
```

---

## Expected Runtime

Each response may take **30 seconds or more** when running on CPU.

This is normal.

---

## Option B - Avaloq-Approved AI Chat Tool

If you are using your Avaloq's approved AI chat tool instead of the Module 0 VM:

1. Open:

```text
lab1_worksheet.txt
```

2. Copy each block into the approved AI chat tool.
3. Run the blocks one at a time.
4. Review each response before continuing.

---

## Safety

> **Use fake alerts only.**

Never use:

- Real production logs
- Real passwords
- API keys or tokens
- Confidential company data
- Personal data
- Other sensitive information

This laboratory is designed for learning and testing using sanitized or synthetic data only.