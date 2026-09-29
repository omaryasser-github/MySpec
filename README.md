# 🎯 MySpec

**MySpec in your AI to your exact skill level.**

MySpec turns your AI into a personalized technical partner. Using 50 interactive questions, it builds a precise profile of your tech stack and learning style to give you custom 60-minute onboarding plans, gap analyses for new projects, and seamless local context. Stop repeating yourself to your AI.

---

## 💡 The Problem

Every time you start a new chat or a new project, your AI resets. You have to explain who you are, what you know, and how you code. If you don't, you get generic, beginner-level tutorials that waste your time.

## 🚀 The Solution

**MySpec** fixes this by establishing your ultimate "AI Spec." Through a carefully designed, fatigue-free interview process, MySpec learns your exact identity, skills, and preferences, outputting a single, highly optimized context file.

Whenever you start a new project, your AI already knows what you know—and exactly what you need to learn.

---

## ✨ Features

* 🧠 **Zero-Fatigue Interview:** 50 curated questions across 7 categories, asked just *two at a time* using advanced state-machine prompting.
* ⚡ **Single-File Context (`profile.md`):** Your entire persona is compiled into one dense file. This prevents the LLM "lost in the middle" effect and ensures lightning-fast retrieval.
* 🌍 **Bilingual Support:** Native prompt templates in English and Modern Standard Arabic (MSA).
* ⏱️ **60-Minute Onboarding:** Bring a new project idea to your "Dialed-In" AI, and it will perform a gap analysis, telling you exactly what to leverage and what new skills to learn in your first hour.
* 🔌 **Local MCP Server:** Run a read-only stdio server that supplies your local profile to existing MCP hosts such as Cursor, Claude Desktop, and Windsurf. The server exposes no network transport and makes no network calls.

---

## 🏗️ System Architecture & Workflow

### 1. System Architecture Overview

![System Architecture Overview](https://mermaid.ink/svg/eyJjb2RlIjogImZsb3djaGFydCBURFxuICAgIFByb21wdFtcIm1hc3Rlci1pbnRlcnZpZXcubWQgLSA1MCBRdWVzdGlvbnNcIl1cbiAgICBXZWJMTE1bXCJXZWIgTExNIC0gQ2hhdEdQVCAvIENsYXVkZSAvIEdlbWluaVwiXVxuICAgIFByb2ZpbGVbKFwiTG9jYWwgUHJvZmlsZSAtIHByb2ZpbGUuanNvbiBvciBwcm9maWxlLm1kXCIpXVxuICAgIE1DUFtcIk15U3BlYyBMb2NhbCBNQ1AgU2VydmVyIC0gc3RkaW8sIHJlYWQtb25seVwiXVxuICAgIElERVtcIkFJIEhvc3QgLSBDdXJzb3IgLyBDbGF1ZGUgRGVza3RvcCAvIFdpbmRzdXJmXCJdXG4gICAgVXBkYXRlW1wicHJvZmlsZV91cGRhdGUubWQgLSBTZW1WZXIgU2tpbGwgRXZvbHV0aW9uXCJdXG5cbiAgICBQcm9tcHQgLS0-fFJ1biBJbnRlcnZpZXd8IFdlYkxMTVxuICAgIFdlYkxMTSAtLT58U2F2ZSBQcm9maWxlfCBQcm9maWxlXG4gICAgUHJvZmlsZSAtLT58QXV0by1EaXNjb3ZlcmVkfCBNQ1BcbiAgICBNQ1AgLS0-fFByb3ZpZGUgQ29udGV4dHwgSURFXG4gICAgSURFIC0tPnxRdWVyeSBDb250ZXh0fCBNQ1BcbiAgICBJREUgLS4tPnxQcm9qZWN0IEV2aWRlbmNlfCBVcGRhdGVcbiAgICBVcGRhdGUgLS4tPnxBcHByb3ZlZCBVcGRhdGVzfCBQcm9maWxlXG4iLCAibWVybWFpZCI6IHsidGhlbWUiOiAiZGVmYXVsdCJ9fQ==)

### 2. End-to-End System Sequence

![End-to-End System Sequence](https://mermaid.ink/svg/eyJjb2RlIjogInNlcXVlbmNlRGlhZ3JhbVxuICAgIGF1dG9udW1iZXJcbiAgICBhY3RvciBEZXYgYXMgRGV2ZWxvcGVyXG4gICAgcGFydGljaXBhbnQgV2ViQUkgYXMgV2ViIExMTVxuICAgIHBhcnRpY2lwYW50IERpc2sgYXMgTG9jYWwgU3RvcmFnZVxuICAgIHBhcnRpY2lwYW50IEhvc3QgYXMgQUkgSG9zdFxuICAgIHBhcnRpY2lwYW50IE1DUCBhcyBMb2NhbCBNQ1AgU2VydmVyXG5cbiAgICBOb3RlIG92ZXIgRGV2LFdlYkFJOiAxLiBEaXNjb3ZlcnkgSW50ZXJ2aWV3XG4gICAgRGV2LT4-V2ViQUk6IFJ1biBtYXN0ZXItaW50ZXJ2aWV3Lm1kXG4gICAgV2ViQUktPj5EZXY6IDI1IGludGVydmlldyBwYWlycyBpbiBFTiBvciBNU0FcbiAgICBEZXYtPj5XZWJBSTogUHJvdmlkZSBhbnN3ZXJzXG4gICAgV2ViQUktPj5EZXY6IEVtaXQgcHJvZmlsZS5qc29uIG9yIHByb2ZpbGUubWRcbiAgICBEZXYtPj5EaXNrOiBTYXZlIHRvIGxvY2FsIHByb2ZpbGUgc3RvcmFnZVxuXG4gICAgTm90ZSBvdmVyIEhvc3QsTUNQOiAyLiBMb2NhbCBBSSBDb25uZWN0aW9uXG4gICAgSG9zdC0-Pk1DUDogU3RhcnQgTUNQIHNlcnZlciBvdmVyIHN0ZGlvXG4gICAgTUNQLT4-RGlzazogUmVhZCBsb2NhbCBwcm9maWxlXG4gICAgTUNQLS0-Pkhvc3Q6IFByb3ZpZGUgc2tpbGxzLCBwcmVmZXJlbmNlcywgYW5kIHN1bW1hcnlcblxuICAgIE5vdGUgb3ZlciBEZXYsSG9zdDogMy4gUHJvamVjdCBPbmJvYXJkaW5nXG4gICAgRGV2LT4-SG9zdDogU3VibWl0IHByb2plY3QgYnJpZWZcbiAgICBIb3N0LT4-TUNQOiBSZXF1ZXN0IGdhcCBhbmFseXNpc1xuICAgIE1DUC0tPj5Ib3N0OiBSZXR1cm4gbWF0Y2hpbmcgc2tpbGxzIGFuZCBnYXBzXG4gICAgSG9zdC0-PkRldjogRGVsaXZlciB0YWlsb3JlZCA2MC1taW51dGUgcGxhblxuXG4gICAgTm90ZSBvdmVyIERldixEaXNrOiA0LiBQb3N0LVByb2plY3QgVXBkYXRlXG4gICAgRGV2LT4-SG9zdDogU3VibWl0IGNvbXBsZXRlZCBwcm9qZWN0IGRlbGl2ZXJhYmxlc1xuICAgIEhvc3QtPj5EZXY6IEdlbmVyYXRlIHByb2ZpbGUgZGVsdGFcbiAgICBEZXYtPj5EaXNrOiBTYXZlIGFwcHJvdmVkIHNraWxsIHVwZGF0ZXNcbiIsICJtZXJtYWlkIjogeyJ0aGVtZSI6ICJkZWZhdWx0In19)

---

## 🛠️ How It Works

1. **The Interview:** You copy our `master-interview` prompt into your favorite LLM (ChatGPT, Claude, Gemini).
2. **The Chat:** The AI acts as a Technical Profiler, asking you targeted questions about your current skills, goals, and limitations.
3. **The Output:** Once completed, the AI generates your personal `profile.md`.
4. **The Execution:** Use your `profile.md` alongside the `prompts/project_onboarding.md` prompt whenever you start something new. Get instant, tailored guidance.

---

### The complete guide

See the complete guide in [`docs/how-it-works.md`](docs/how-it-works.md) and the implementation record in [`docs/phases/phase-07-how-it-works.md`](docs/phases/phase-07-how-it-works.md).

### Local MCP Server

Adds a local-only stdio MCP server for reading the MySpec profile and supplying context to an existing AI host. See [`mcp-server/README.md`](mcp-server/README.md) for installation and host configuration, and [`docs/phases/phase-08-local-mcp-server.md`](docs/phases/phase-08-local-mcp-server.md) for the architecture and validation scope.

## ⚡ Quick Start

Ready to lock in your AI context?

1. Navigate to the `prompts/` directory and open `master-interview.md` (Choose your preferred language).
2. Copy the entire prompt text.
3. Paste it into a new chat with your preferred AI model.
4. Answer the questions as they come.
5. Save the final output to `~/.myspec/profile.md` (or `~/.myspec/profile.json`).

> **Pro Tip:** Keep your profile file handy in `~/.myspec/`! You can paste it into ChatGPT's Custom Instructions, Claude's Project Knowledge, or let the local MCP server discover it automatically.

---

## 🤝 Contributing

MySpec is an open-source movement to make AI interactions more human and tailored. We welcome contributions, whether it's refining the prompts, adding new language translations, or improving the local MCP server!

---
