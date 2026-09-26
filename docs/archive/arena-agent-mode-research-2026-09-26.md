<!-- Source: Google Drive, Arena.ai Agent Mode Research; retrieved 2026-09-26. -->
> **Source document:** [Arena.ai Agent Mode Research](https://docs.google.com/document/d/1WxaodVW4FvzoWvmJ1SU4M1Lz_w6uNMkoBSTssztPKY8/edit) (Google Drive, 2026-09-26).
> **Evidence notice:** This is a research-source transcription, not an independently verified capability manifest. Claims and classifications reflect the source document; compare with the repository's empirical probe results before treating them as operational facts.

# ARENA AI — INDEPENDENT CAPABILITY AND PRODUCT RESEARCH

## Official Technical Evaluation & Capability Ledger | September 26, 2026

## Executive Summary

The artificial intelligence evaluation landscape has undergone a foundational paradigm shift, moving away from single-turn model benchmarking toward the assessment of long-horizon, autonomous multi-step problem solving. Central to this transition is Arena.ai, an ecosystem originally recognized for crowdsourced chatbot leaderboards that has fundamentally evolved into a persistent, containerized fullstack AI development and evaluation environment. Having achieved a $100 million annualized revenue run rate in its first eight months and currently serving over ten million monthly users, Arena represents one of the largest human-preference evaluation platforms operating in production1.

On June 4, 2026, Arena officially introduced "Agent Mode," pivoting the interface from a static conversational window into a dynamic execution workspace capable of managing complex, iterative workflows3. This independent research report delivers an exhaustive, source-grounded technical investigation into Arena's Agent Mode as of September 26, 2026. The ensuing analysis isolates officially documented platform capabilities from third-party phenomena and user-generated workarounds. It heavily scrutinizes the architectural "harness tax" overhead discovered by external researchers, provides a strict evidence classification ledger detailing integrations, outlines severe technical limitations, and defines practical workflows.

To ensure strict independence from AI-generated self-assessments, every significant technical claim evaluated in this report is categorized into one of five evidence tiers: DOCUMENTED, OBSERVED_IN_PUBLIC_EXAMPLES, THIRD_PARTY_REPORTED, NOT_VERIFIED, or NOT_SUPPORTED_BY_AVAILABLE_SOURCES. Furthermore, this report isolates Agent Mode from unrelated product modalities, such as Copilot Arena, ensuring that agentic capabilities are not falsely inferred from strictly inline-editing or fill-in-the-middle (FiM) code completion environments5.

## 1. Agent Mode Architecture and Orchestration

The foundational architecture of Arena Agent Mode Abandons left-to-right text generation in favor of a multi-turn, multi-step autonomous execution framework. This environment is built upon the ReAct (Reasoning and Acting) paradigm, ensuring that rather than forcing models to output static code blocks in a vacuum, the platform encapsulates models within an interactive harness. Here, models must dynamically formulate plans, emit structured tool calls, observe environmental feedback, and recursively refine their actions over extended horizons DOCUMENTED4.

### The Causal Feedback Architecture

Because long-horizon agents can succeed or fail across hundreds of turns, Arena replaced static benchmarking with a causal evaluation framework that captures a continuous stream of environmental and human feedback DOCUMENTED. Every execution trajectory is logged, versioned, and stored as traceable state snapshots in Cloudflare R27.

The causal feedback architecture relies on a continuous loop of reasoning and tool calling. Specifically, the system routes the model's outputs into a structured tool schema, which executes within the isolated containerized sandbox. The resulting telemetry—comprising bash exit codes and standard tool errors—flows into a feedback array alongside human supervisory signals. These human signals include explicit praise or complaints derived from natural language parsing, as well as steerability metrics that track the agent's compliance with in-line corrections. These combined data streams are captured by a Cloudflare R2 logger to formulate the final causal evaluation score and dictate leaderboard positioning7.

The platform aggregates five primary causal signals from these logged traces:

- Confirmed Success: The ultimate determinant of task completion, measured by explicit user approval or disapproval via the platform's user interface upon the conclusion of a trajectory8.
- Praise vs. Complaint Sentiment: An automated measurement of natural language feedback within the session. A task trajectory is classified as successful if explicit verbal praise (e.g., "this is exactly what I needed") mathematically outnumbers explicit verbal complaints8.
- Steerability: A metric calculating the agent's ability to successfully ingest and execute in-line user corrections. If an agent corrects its course after a user intervention, the steerability metric improves; if the user rejects the fix or abandons the session, the metric degrades8.
- Bash Recovery Clock: A strict operational metric that activates when an agent issues a shell command resulting in an error due to a model hallucination or syntax failure. The clock counts the number of subsequent bash calls required to reach a non-erroring state. Agents that abandon the task before recovery receive severe statistical penalties8.
- Tool Hallucination Penalties: A stringent safeguard that immediately fails a task if the agent attempts to call a non-existent tool, generates malformed syntax resulting in a junk tool name, or leaks internal chain-of-thought tokens into the tool execution JSON field8.
### The Harness Tax and Component Ablation

The orchestration surrounding the core language model—specifically the agent "harness" comprising tool definitions, system prompts, context management, and execution wrappers—has been empirically proven to drastically alter operational costs. A landmark September 16, 2026 study conducted by researchers at UC Berkeley's Sky Computing Lab and Arena evaluated 21 model-harness pairs across the SWE-bench Lite and Terminal-Bench 2.0 datasets DOCUMENTED9. The researchers discovered the "Harness Tax": swapping the agent harness alters task success rates by an insignificant margin (±2% on SWE-bench Lite), but can swing the financial cost of achieving that success by up to 500%9.

The analysis attributes this massive variance directly to initial context bloating. Proprietary heavy harnesses, such as Claude Code, inject over ten times the initial context tokens (averaging up to 27,000 tokens of overhead) compared to minimal open-source harnesses like Pi (which operates on approximately 2,600 tokens of overhead). Consequently, a model like Claude Fable 5 achieved a 97.8% success rate inside the Claude Code harness for $1.33 per attempt, but achieved a statistically identical 96.7% success rate inside the minimal Pi harness for only $0.67 per attempt. The heavy harness doubled the cost for a marginal 1.1% gain in correctness THIRD_PARTY_REPORTED9.

Expanding upon harness architecture, an exhaustive 43-page peer-reviewed study published on September 17, 2026 (arXiv:2609.20804) ran 176 ablation configurations to isolate individual harness components THIRD_PARTY_REPORTED12. By holding the execution loop fixed across models such as Nemotron-3 (30B, 120B, 550B) and Mistral-Medium-3.5-128B, the researchers demonstrated that context management is primarily an insurance policy against context-overflow failures in long-running tasks. They found that staging static, rule-based elision (mechanically scrubbing redundant grep outputs and compiler warnings before they touch the model) prior to invoking LLM-based summarization yields the highest efficiency14. Furthermore, allowing the agent to dynamically recover elided text added unnecessary prompt complexity and state machinery without yielding any measurable accuracy improvements15. The study also revealed that planning modules act as an accuracy scaffold for weaker models, but for highly capable frontier models, planning merely acts as a financial brake to prevent runaway token expenditure14. Additionally, providing predefined bespoke tools proved beneficial for models with weak bash proficiency, but bash-capable models operated far more effectively and cheaply using a raw bash-only interface15.

## 2. Comprehensive Capability Inventory

The following subsections systematically investigate the 16 core dimensions of Agent Mode, separating official platform capabilities from user-engineered phenomena.

### Actual Built-In Tools

Agent Mode equips models with a specific suite of built-in capabilities that they can autonomously invoke during a session DOCUMENTED4.

- Filesystem Operations: Agents natively possess the create_file, edit_file, and read_file schemas to navigate and mutate the multi-file workspace7.
- Shell Execution: The run_command or bash tool grants the agent direct access to an isolated Linux shell environment, expanding its capabilities beyond static file modification to include package installation and script execution17.
- Web Search: A real-time data retrieval tool allowing the agent to lookup external APIs, documentation, and live data feeds17.
- Multimodal Generation: Visual asset creation and editing tools powered by the platform's multimodal routers4.
- Version Control: github_connect, push_changes, and open_pr schemas for manipulating remote repositories18.
It is critical to distinguish between tool availability and model capability. While a model may possess the cognitive capability to analyze a complex spreadsheet format, it can only autonomously execute code to parse that spreadsheet if the harness explicitly exposes the requisite tool schema. Arena's toolset relies heavily on the bash environment to bridge any gaps in native tool availability.

### Web Search and Deep Research

The integration of real-time web search transforms Agent Mode from an isolated coding sandbox into a continuous research-to-implementation environment DOCUMENTED. Agents are equipped to independently pause execution, query the web for real-time information or updated software documentation, and immediately apply those findings to the active codebase4.

Public session traces reveal sophisticated multi-stage web synthesis tasks OBSERVED_IN_PUBLIC_EXAMPLES. In one recorded trace, a model autonomously built a live sports-TV schedule application. The agent searched across various Italian television and streaming guide websites, aggregated the daily broadcast data, merged duplicate event entries across disparate sources, and constructed a password-protected administrative dashboard to monitor the health of the incoming data feeds. This entire deep research and aggregation workflow occurred autonomously across 140 turns and 448 tool calls, culminating in a functional, deployable web application8.

### Sandbox and Terminal Environment

Arena's Fullstack Code Arena update, launched on July 8, 2026, fundamentally upgraded the execution environment from a single-page frontend prototyper into a persistent, production-grade development sandbox DOCUMENTED17.

The environment operates within isolated, long-running Linux containers. Unlike ephemeral chat sessions, these sandboxes offer full data persistence, allowing complex applications to store user data across multiple sessions (e.g., educational platforms that maintain state when a user logs out and returns days later)17. The backend infrastructure includes native support for PostgreSQL databases, complete with user authentication flows and Row Level Security (RLS) policies, enabling the generation of secure, members-only applications17.

The user interface features a live visual terminal that exposes the agent's bash command execution in real time17. Code generation is streamed and rendered utilizing CodeMirror 6 for precise source viewing, while an embedded live development server provides continuous hot-reloading7.

### Supported Programming Languages

While Agent Mode's terminal allows the compilation and execution of virtually any language supported by a standard Linux environment, official platform telemetry highlights a distinct distribution of languages utilized by the user base DOCUMENTED. The vast majority of code generation in the Arena ecosystem relies on Python, followed by JavaScript, TypeScript, HTML/CSS, and C++5. Furthermore, the introduction of Fullstack Code Arena officially expanded the platform's native support to include SQL for PostgreSQL database generation and schema management17.

### Browser Automation and Playwright

When evaluating browser automation capabilities, a strict distinction must be drawn between native harness tools and environment-level execution software. Official Arena documentation does not list Playwright, Selenium, or any other headless browser driver as a native, built-in tool schema exposed to the agent NOT_SUPPORTED_BY_AVAILABLE_SOURCES4.

However, because the agent possesses unrestricted bash access within its Linux sandbox, it is fully capable of executing commands such as npm install playwright or pip install playwright OBSERVED_IN_PUBLIC_EXAMPLES17. Once installed, the agent can write scripts utilizing the Playwright library and execute them via the terminal. This signifies that while the sandbox supports the installation and execution of browser automation frameworks, Playwright is not a distinct, orchestrator-level agentic tool provided by the Arena harness itself.

### File Generation and Workspace Downloads

Agent Mode transcends text output by generating and manipulating tangible files. The platform supports the creation of standard development files (source code, markdown, JSON), as well as complex formats including .docx, .pptx, .xlsx, and .pdf DOCUMENTED4.

Because the execution environment is a persistent multi-file workspace, users do not need to manually copy and paste individual code blocks. Upon the conclusion of a session, the entire containerized project—including the generated backend logic, frontend assets, database schemas, and synthesized documents—can be downloaded directly as a complete .zip workspace archive4.

### GitHub Integration and Development Workflows

On August 17, 2026, Arena introduced deep version control integration, allowing developers to connect their GitHub repositories directly into the Agent Mode interface DOCUMENTED18. This fundamentally shifts the platform's utility from isolated prototyping to direct codebase maintenance.

Agents can natively read existing repositories, analyze directory structures, and implement code modifications. Users can oversee this process through a newly introduced dedicated visual diff panel, which tracks the agent's proposed code modifications line-by-line in real time18. Once the user approves the edits, the agent can autonomously push the commits back to the connected repository and open fully formatted pull requests without the user ever leaving the browser interface18.

### Application Preview and Development Servers

To facilitate the immediate evaluation of fullstack builds, Agent Mode features a persistent live development server integrated directly into the sandbox DOCUMENTED17. As the agent iteratively writes and edits code, the resulting application is continuously built and streamed through a secure frontend preview pane with hot-reloading capabilities7.

For production deployment, Arena has engineered a seamless build-to-ship pipeline integrated with Vercel. Once a fullstack web application is deemed complete within the sandbox, it can be exported and deployed directly to Vercel's hosting infrastructure, finalizing the rapid prototyping lifecycle17.

### Multimodal Functionality

Arena expanded beyond pure text processing with the introduction of the "Max" multimodal router on May 5, 2026 DOCUMENTED3. Powered by over five million community votes, Max acts as an intelligent orchestrator that dynamically routes user prompts to the most capable model for a specific task modality, ensuring optimal performance while tightly controlling response latency20.

Through this multimodal expansion, Agent Mode natively supports vision analysis, image generation, and image editing. This allows agents to seamlessly transition from writing frontend code to generating the required visual assets for that user interface within a single cohesive session3. Furthermore, specialized evaluation environments such as Image Arena, Video Arena, and Document Arena provide granular performance tracking for multi-modal assets across the wider ecosystem3.

### Supported Uploads and Outputs

Agent Mode acts as a sophisticated bidirectional data processing engine DOCUMENTED.

- Inputs: Users can upload file attachments (including PDFs, text documents, and images) directly into the agent's context. Crucially, the platform supports the secure ingestion of third-party API keys. This allows users to inject credentials for external services—such as an OpenAI API key for a generated chatbot application, or a Stripe payment gateway key for an e-commerce platform—enabling the agent to securely connect the generated code to real-world backend services4.
- Outputs: The system exports live web applications, raw .zip workspaces, standalone documents, image assets, and direct GitHub pull requests4.
### Model Selection and Transparency

Arena allows users to explicitly select which frontier model powers their Agent Mode session, ensuring total transparency over the underlying intelligence DOCUMENTED. As of September 2026, the available model roster includes top-tier proprietary and open-weight systems, including Anthropic's Claude Opus 5.5 Max and Claude Fable 5.1 Max, OpenAI's GPT-6 Astra Max and GPT-5.6 Sol Max, Moonshot's Kimi K3 Max, Alibaba's Qwen 3.8 Max, DeepSeek's V4.1 Flash, SpaceXAI's Grok 4.7, and Google's Gemini 3.7 Flash21.

The platform enforces strict evaluation transparency. The leaderboards publicly display the raw input and output token pricing (cost per million tokens) alongside the maximum context window length for every single model. Performance metrics are derived using an open-source Python package (arena-rank) that applies a Bradley-Terry ranking model to calculate Elo ratings and 95% confidence intervals based on real human preference data, completely rejecting vendor-supplied self-assessments21.

### Context and Session Handling

The scope of tasks performed in Agent Mode demands massive context windows. Models on the platform support context lengths scaling from 128,000 tokens up to 2,000,000 tokens21.

Empirical trace data from real-world Agent Arena usage underscores the sheer volume of data processed during autonomous workflows DOCUMENTED. Statistics derived from seven-day trailing windows reveal that 32% of all agent sessions end with at least 128,000 input tokens in their final turn. Furthermore, 22% of sessions reach at least 256,000 tokens, and 8% of sessions exceed 1,000,000 tokens by the time the task is completed or abandoned8. Sessions are fully persistent and shareable; users can pause a long-running execution and restore the exact environment state at a later date, relying on the Cloudflare R2 infrastructure to fetch the frozen execution state7.

### Usage Limits and Availability

Agent Mode is globally available to all users via the main web interface (arena.ai/agent) and can be integrated into external CLI tools via API gateway endpoints (api.preview.arena.ai) DOCUMENTED19. The platform processes immense scale, surpassing 5 million agent turns in its first month and maintaining a 10% week-over-week growth rate2.

To control the exorbitant computational costs associated with runaway recursive loops, Arena enforces strict usage caps during evaluation benchmarking. As detailed in the HarnessTax studies, agent attempts in controlled environments are strictly capped at a maximum of 100 agent turns per evaluation attempt to mitigate infinite execution loops9.

### Privacy, Permissions, and Data Handling

Arena operates fundamentally as an open-science, human-preference data collection engine, which carries significant implications for corporate privacy DOCUMENTED. Data generated on the platform—including conversation histories, executed code, rendered applications, and human voting patterns—is actively utilized to populate public leaderboards and is frequently released as open-source datasets (such as lmarena-ai/arena-human-preference-140k) for the broader AI research community24.

While the platform anonymizes model identities during Battle Mode and scrubs explicitly identifiable telemetry, Arena's official privacy documentation explicitly warns users to avoid submitting sensitive, proprietary, or personal confidential information during their interactions27. Consequently, uploading highly classified enterprise codebases into the public Agent Mode sandbox presents severe data leakage risks, and no zero-data-retention guarantees are supported for the public tier NOT_SUPPORTED_BY_AVAILABLE_SOURCES.

### Undocumented or Experimental Capabilities Requiring Empirical Testing

While the platform's broad strokes are heavily documented, several operational constraints remain obscured and require live, empirical probes to quantify NOT_VERIFIED:

- Sandbox Shell Timeouts: The absolute wall-clock timeout limit for executing long-running asynchronous bash scripts (e.g., compiling heavy C++ binaries, generating expansive PDF reports from raw data, or executing prolonged Playwright web scraping tasks) inside the container is not officially specified.
- Filesystem Quotas: The maximum disk space allocation (in gigabytes) permitted per isolated workspace container before encountering out-of-storage errors remains undocumented.
- Third-Party API Rate Limiting: The platform's behavior and potential internal throttling mechanisms when a user supplies a third-party API key for high-concurrency background processing (e.g., executing thousands of concurrent OpenAI requests from within the agent's Node.js server) are currently unknown.
## 3. Evidence and Source Ledger

The following ledger strictly classifies all significant technical claims evaluated in this report against their corresponding evidence tiers, source references, and publication dates to ensure auditable rigor.

| Capability / Claim | Evidence Classification | Publication / Update Date |
| --- | --- | --- |
| Agent Mode Multi-Step Architecture & ReAct Loop | DOCUMENTED | Nov 12, 2025 / June 04, 2026 |
| Causal Feedback (Steerability, Bash Clock, Sentiment) | DOCUMENTED | June 04, 2026 |
| HarnessTax: 5x Cost Overhead Variance vs. Open Harnesses | DOCUMENTED | Sept 16, 2026 |
| Component Ablation (Rule-based Elision, Recoverable Context) | THIRD_PARTY_REPORTED | Sept 17, 2026 |
| Fullstack Postgres, RLS Auth & Persistent Dev Server | DOCUMENTED | July 08, 2026 |
| Web Search & Deep Research Tools via API | DOCUMENTED | July 08, 2026 |
| Native Playwright Headless Browser Agent Tool | NOT_SUPPORTED_BY_AVAILABLE_SOURCES | N/A |
| Terminal Playwright Installation via npm/pip bash commands | OBSERVED_IN_PUBLIC_EXAMPLES | July 08, 2026 |
| GitHub Direct Sync, Pushes, and Real-Time Visual PRs | DOCUMENTED | Aug 26, 2026 |
| Vercel Direct Deployment Pipeline Integration | DOCUMENTED | July 08, 2026 |
| Multimodal Max Router (Vision/Image Gen orchestration) | DOCUMENTED | May 05, 2026 |
| Empirical Session Logs: 32% Sessions Reaching ≥128k Tokens | DOCUMENTED | June 04, 2026 |
| Public Release of Anonymized Chat Logs (Data Privacy Limit) | DOCUMENTED | Current (2026) |

## 4. Technical Limitations

Despite Agent Mode's robust capabilities, the platform exhibits severe technical constraints that must be accounted for in production workflows.

The primary limitation is the Harness Tax and Context Overhead. As demonstrated by the UC Berkeley studies, complex proprietary harnesses drastically inflate token consumption on the very first API call by injecting massive tool schemas and system instructions. Because this overhead is appended to every subsequent turn, long-running agentic tasks suffer from exponential cost scaling without delivering proportional increases in task success. A harness utilizing 27,000 overhead tokens will rapidly consume budgets compared to an open alternative utilizing 2,600 tokens9.

This inflation directly triggers the second major constraint: Context-Window Degradation. Even with model limits extending to 2 million tokens, the continuous accumulation of shell outputs and file modifications rapidly degrades prefill latency and introduces severe context-overflow risks. As outlined in the arXiv:2609.20804 ablation study, unless the agent is equipped with aggressive, rule-based text elision to scrub redundant compiler warnings, it will inevitably crash mid-loop on complex tasks14.

Furthermore, Tool Hallucination remains an active vulnerability. Agents occasionally fabricate nonexistent tool names or bleed internal chain-of-thought logic into their structured JSON tool schemas, triggering immediate task failures under Arena's stringent bash telemetry logic8.

Finally, the platform's foundational reliance on crowdsourced data telemetry for its leaderboards makes it fundamentally incompatible with Strict Enterprise Privacy requirements. Because user prompts and codebase snapshots are routinely exposed to open-source evaluation datasets, organizations cannot utilize the public web interface for highly classified, proprietary code maintenance27.

## 5. Evaluation of Supplementary Platforms and Practical Workflow Recommendations

Based on the verified capabilities of the execution sandbox, web search tools, and GitHub integrations, Arena Agent Mode serves as a highly effective supplementary platform for the following practical workflows:

1. Deep Research and Research-to-Implementation Workflows Agent Mode's integration of live web search with a bash terminal enables profound research-to-implementation cycles. Practitioners can command the agent to synthesize complex technical documentation on novel APIs, scrape relevant developer forums for implementation strategies, and immediately draft, execute, and test integration scripts within the live bash terminal. The persistent session allows for a seamless transition from theoretical research to a fully functional, containerized prototype4.

2. Fullstack Coding Agents and App Prototyping The platform excels as a rapid prototyping engine for fullstack applications. Developers can leverage the PostgreSQL backend and RLS auth capabilities to scaffold complex React or Next.js applications, test backend logic in the visual terminal, and subsequently deploy the finished prototype directly to Vercel. The live CodeMirror 6 rendering ensures immediate visual feedback7.

3. GitHub Maintenance and Code Auditing By connecting open-source repositories directly to the Agent Mode interface, engineering teams can perform routine code auditing without cloning repositories locally. The agent can review specific directories, implement stylistic refactoring, run unit tests in the container, and generate pull requests using the real-time diff panel18.

4. Website Auditing, SEO, and Technical Analysis While lacking a native Playwright schema, the agent's bash access allows it to execute shell scripts utilizing standard Linux tools (like cURL, wget, or Python's BeautifulSoup). This enables the agent to scrape sitemaps, analyze payload sizes, verify metadata headers, and assess overall SEO technical compliance across external domains8.

5. Report Generation and Documentation Agent Mode can ingest massive datasets, PDFs, or raw log files into its context window. The agent can execute data analysis via Python scripts in the sandbox, synthesize the findings, and generate formatted markdown, .docx, or .pdf reports. It can also act as an automated documentation engine, ingesting a raw repository and outputting comprehensive Markdown wikis or API references4.

6. Browser Testing Browser testing remains a supplementary, experimental workflow. Users must instruct the agent to utilize bash to install headless testing frameworks (e.g., npm install playwright) and write bespoke Node.js testing scripts. The platform does not natively abstract browser testing into an orchestrator-level tool, requiring explicit user guidance to scaffold the testing environment17.

## 6. Comparative Analysis: Arena vs. Google Opal vs. Dedicated Coding Agents

To accurately situate Arena's practical utility, it must be contrasted with emerging visual AI orchestrators and localized agent environments. The market is increasingly bifurcating into visual workflow automation, cloud-based fullstack evaluation, and localized enterprise coding.

Arena AI Agent Mode is a terminal-centric, code-first evaluation environment. It is designed for developers, entrepreneurs, and AI researchers, utilizing a ReAct bash loop, direct filesystem manipulation, and GitHub synchronization to build and evaluate fullstack applications17. It succeeds in providing a high-fidelity, isolated sandbox for benchmarking software-engineering AI, exposing the raw terminal execution to the user.

Google Opal (Google Labs), conversely, operates as a visual, no-code mini-app builder designed for educators, non-technical professionals, and rapid prototyping. Introduced in 2025, Opal abandons the bash terminal in favor of a drag-and-drop flowchart canvas. Users connect input blocks to generation nodes powered exclusively by the Google ecosystem (Gemini 3 Flash, Veo 3.1, Nano Banana Pro). While Opal features an "Agent Mode," this mode acts as a dynamic routing mechanism between fixed visual blocks, rather than a recursive coding loop. Rather than deploying to Vercel or pushing to GitHub, Opal outputs directly to Google Workspace (Docs, Slides, Sheets) or published web links29. It is vastly superior for non-technical workflow automation, but entirely incapable of maintaining a complex React repository.

Dedicated Local Coding Agents (e.g., Z AI, Cursor, Claude Code CLI) exist directly on the user's local machine. Unlike Arena's isolated cloud containers, these agents have unrestricted access to the user's actual host filesystem, local environment variables, and proprietary IDE configurations. For instance, open-source localized agents like Z AI, powered by GLM 4.7, offer offline capability and desktop automation without the subscription fees or cloud privacy risks associated with public platforms32. Furthermore, local deployments allow engineering teams to bypass the "harness tax" by configuring minimal, custom open-source harnesses, significantly reducing overhead token costs33. While Arena is optimal for sandbox testing and multi-model benchmarking without local setup, dedicated local agents remain the mandatory standard for engineers operating on highly secure, enterprise-grade, localized codebases33.

#### Works cited

- Arena Blog, https://arena.ai/blog
- Arena Reaches $100M in 8 Months, https://arena.ai/blog/arena-100m-revenue
- Arena Blog, https://arena.ai/blog/category/product
- Empowering Users to Get More Done With Agent Mode - Arena AI, https://arena.ai/blog/agent-mode
- Copilot Arena, https://arena.ai/blog/copilot-arena/
- Code Editing in Copilot Arena - Arena AI, https://arena.ai/blog/code-editing-in-copilot-arena-copilot
- The Next Stage of AI Coding Evaluation Is Here - Arena AI, https://arena.ai/blog/code-arena
- Agent Arena: Causal Evaluation of Agents in the Real World - Arena AI, https://arena.ai/blog/agent-arena-methodology
- HarnessTax: How Much Does the Harness Matter for Coding Agents?, https://arena.ai/blog/coding-agents-harness-tax
- The model sets the success rate. The harness sets the bill. Here's, https://varops.com/the-model-sets-the-success-rate-the-harness-sets-the-bill-heres-where-the-money-goes/
- Agent Harness Choice Moves Cost, Not Accuracy - Selfship, https://selfship.ai/blog/agent-harness-choice-cost-not-accuracy/
- 176-config study finds one context trick that wins | MindPattern, https://mindpattern.ai/s/176-configuration-harness-ablation-rule-based-elision-before-llm-summarization-is-the-best-conte
- An Empirical Study of Harness Design for Coding Agents - arXiv, https://arxiv.org/abs/2609.20804
- Paper page - An Empirical Study of Harness Design for Coding Agents, https://huggingface.co/papers/2609.20804
- The coding agent harness paper finally ran component ablations, https://dev.to/reidmarlow/the-coding-agent-harness-paper-finally-ran-component-ablations-1n39
- An Empirical Study of Harness Design for Coding Agents - arXiv, https://arxiv.org/html/2609.20804v1
- Build, Deploy, and Evaluate with Fullstack Code Arena - Arena AI, https://arena.ai/blog/fullstack-code-arena
- Product Changelog - Arena.ai, https://arena.ai/company/product-changelog
- Agent Mode | Autonomous AI Agents for Real-World Tasks - Arena AI, https://arena.ai/agent
- Introducing Max - Arena AI, https://arena.ai/blog/introducing-max
- WebDev AI Leaderboard - Arena AI, https://arena.ai/leaderboard/code/webdev?rankBy=labs
- Brand & Marketing - Arena AI, https://arena.ai/leaderboard/code/webdev/brand-marketing
- Code Arena WebDev leaderboard, https://arena.ai/leaderboard/code/webdev
- Arena-Rank: Open Sourcing the Leaderboard Methodology, https://arena.ai/blog/arena-rank
- March 2026: Arena Updates across Product, Leaderboard Rankings, https://arena.ai/blog/march-2026-arena-updates
- Connect Claude Code and Desktop - Arena AI, https://portal.api.preview.arena.ai/docs/windows
- AI Leaderboards, Benchmarks, and Arena Explained - Arena FAQ, https://arena.ai/faq
- How Arena Works | AI Model Evaluation & Benchmarking, https://arena.ai/how-it-works
- Google Opal Tutorial: Build No-Code AI Apps in Minutes - LBSocial, https://www.lbsocial.net/post/google-opal-tutorial-no-code-ai-apps
- Opal AI: Build Google AI Mini-Apps - AnyGen, https://www.anygen.io/showcase/opal-ai/index.html
- The Google AI Tool That Builds Apps For You - Learn Prompting, https://learnprompting.org/blog/google-ai-tool-that-builds-apps-for-you
- Free AI Agent Alternative: Z AI vs Claude Cowork - Reddit, https://www.reddit.com/r/AISEOInsider/comments/1qj3b40/free_ai_agent_alternative_z_ai_vs_claude_cowork/
- Builder Radar — Week of September 20, 2026 - Buttondown, https://buttondown.com/Builder-Radar/archive/builder-radar-week-of-september-20-2026/
- Coding Agent Harness: Same Model, 2x the Cost | Proje Defteri, https://projedefteri.com/en/blog/coding-agent-harness-cost-comparison/
- Best Google Antigravity Alternatives & Competitors - SourceForge, https://sourceforge.net/software/product/Google-Antigravity/alternatives
