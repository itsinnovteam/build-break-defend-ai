# build-break-defend-ai
### Security for AI Bootcamp

A hands-on bootcamp for DevOps and security engineers (and anyone technically literate but new to AI) that goes from using AI, to trusting it, to building, automating, and securing it.

Progression: **use it → trust it → build with it → automate with it → secure it**

Every module has a lab. You build something, then break it, then learn how much to trust it.

## Who it's for
DevOps/SRE, security engineers, and anyone technically strong but new to building with AI. No prior AI knowledge required.

## Why this bootcamp
- Hands-on build/break/defend, not just theory
- Security is threaded through every module, not bolted on at the end
- Built for regulated-enterprise reality: access control, compliance, deployment patterns

## Curriculum

| Module | Topics | Lab |
|---|---|---|
| 0 - How LLMs actually work | tokens, context window, hallucinations, sampling/temperature, capabilities & limits | Induce hallucinations, test security threads, learn when the model is reliable |
| 1 - Practical fluency | prompting, structured outputs, custom instructions, feeding context, iterative refinement | Chat to tool - real work, locking format, stress-testing trust |
| 2 - AI in the engineering & security workflow | best practices, review discipline, failure modes, security uses | Trust but verify AI code - hunt the issue, fix, meta-review |
| 3 - From chat to API | messages/roles, system prompts, structured output, cost/tokens, security | Build a CLI triage tool |
| 4 - Grounding AI in internal data (RAG) | why RAG, the pipeline, tradeoffs, access control, data residency | Build a RAG assistant, then break its access control |
| 5 - Agents and automation | tool calling, agent loop, MCP, when not to use agents, securing agent tools | Build an agent, then hijack it |
| 6 - Secure AI engineering | threat modeling, OWASP LLM Top 10, data governance, deployment patterns, compliance | Make the Lab 5 agent deployment-grade - a threat model defensible in front of a CISO |

## Repository structure

```
build-break-defend-ai/
├── README.md
│
├── modules/
│   ├── 00-how-llms-work/
│   │   ├── README.md
│   │   └── lab-0/
│   │   └── Module0-HowLLMsActuallyWork.pdf
│   ├── 01-practical-fluency/
│   │   ├── README.md
│   │   └── lab/
│   ├── 02-ai-in-the-workflow/
│   │   ├── README.md
│   │   └── lab/
│   ├── 03-chat-to-api/
│   │   ├── README.md
│   │   └── lab/
│   ├── 04-grounding-with-rag/
│   │   ├── README.md
│   │   └── lab/          # includes attack/ for breaking access control
│   ├── 05-agents-and-automation/
│   │   ├── README.md
│   │   └── lab/          # includes attack/ for hijacking the agent
│   └── 06-secure-ai-engineering/
│       ├── README.md
│       └── lab/
│
└── shared/
    ├── prompts/
    ├── datasets/
    └── scripts/
```

Each module is self-contained: its content and its lab (starter, attack if applicable, solution) live together. `shared/` holds anything reused across modules, like the triage dataset that reappears in Module 4.

## Getting started
```bash
git clone https://github.com/<org>/build-break-defend-ai.git
cd build-break-defend-ai
cat docs/prerequisites.md
```
Start at `modules/00-how-llms-work/` and go in order.
