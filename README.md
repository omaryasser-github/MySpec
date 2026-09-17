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
* 🌍 **Trilingual Support:** Native prompt templates in English, Modern Standard Arabic (MSA), and Egyptian Arabic.
* ⏱️ **60-Minute Onboarding:** Bring a new project idea to your "Dialed-In" AI, and it will perform a gap analysis, telling you exactly what to leverage and what new skills to learn in your first hour.
* 🔌 **MCP Ready (Coming Soon):** Designed to integrate with local Model Context Protocol (MCP) servers, feeding your profile directly into IDEs like Cursor and Claude Desktop automatically.

---

## 🛠️ How It Works

1. **The Interview:** You copy our `master-interview` prompt into your favorite LLM (ChatGPT, Claude, Gemini).
2. **The Chat:** The AI acts as a Technical Profiler, asking you targeted questions about your current skills, goals, and limitations.
3. **The Output:** Once completed, the AI generates your personal `profile.md`.
4. **The Execution:** Use your `profile.md` alongside our `project-onboarding` prompt whenever you start something new. Get instant, tailored guidance.

---

## ⚡ Quick Start

Ready to lock in your AI context?

1. Navigate to the `prompts/` directory and open `master-interview.md` (Choose your preferred language).
2. Copy the entire prompt text.
3. Paste it into a new chat with your preferred AI model.
4. Answer the questions as they come.
5. Save the final output as your `profile.md`.

> **Pro Tip:** Keep your `profile.md` handy! You can paste it into ChatGPT's Custom Instructions, Claude's Project Knowledge, or use it with our upcoming local MCP server.

---

## 🤝 Contributing

MySpec is an open-source movement to make AI interactions more human and tailored. We welcome contributions, whether it's refining the prompts, adding new language translations, or building out the MCP server!

---