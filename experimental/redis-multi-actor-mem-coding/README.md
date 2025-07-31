<div align="center">
  <a href="https://github.com/topoteretes/cognee">
    <img src="https://raw.githubusercontent.com/topoteretes/cognee/refs/heads/dev/assets/cognee-logo-transparent.png" alt="Cognee Logo" height="60">
  </a>

  <br />

  # Multi-Actor, Multi-Project Memory Layer with Cognee MCP

  **Building Cross-Tool Intelligence for Software Development Teams**

  <p align="center">
  <a href="https://www.youtube.com/watch?v=1bezuvLwJmw&t=2s">Demo</a>
  ·
  <a href="https://cognee.ai">Learn more</a>
  ·
  <a href="https://discord.gg/NQPKmU5CCg">Join Discord</a>
  ·
  <a href="https://www.reddit.com/r/AIMemory/">Join r/AIMemory</a>
  </p>
</div>

> **Note**: This is a fork of [cognee-mcp](https://github.com/topoteretes/cognee/tree/main/cognee-mcp). For setup instructions and more details, please refer to the original repository.

This implementation showcases how Cognee's memory engine can create a unified knowledge layer across multiple development tools, CI/CD systems, and projects. By leveraging Redis as the vector store, we enable fast, scalable memory operations that can track and analyze patterns across your entire development ecosystem.

The system is exposed through the Model Context Protocol (MCP), making it accessible from any MCP client - whether that's an IDE like Cursor or VS Code, a terminal application, or a CI/CD pipeline.

## ✨ Core Features

- **Multiple transports** – HTTP (recommended for web), SSE (real-time streaming), or stdio (default)
- **Integrated logging** – All actions logged to rotating file and console in dev mode
- **Background pipelines** – Long-running cognify & codify jobs with progress tracking
- **Multi-dimensional memory** – Track by source (IDE/CI/Build) and project simultaneously
- **Redis vector storage** – Sub-millisecond queries for team-wide deployments
- **Full provenance tracking** – Know who used what tool, when, and in which context

## 🎯 The Challenge

Software development involves numerous tools and actors:
- **IDEs**: Cursor, VS Code, WindSurf, JetBrains
- **CI/CD Systems**: GitHub Actions, Jenkins, GitLab CI
- **Build Tools**: Docker, Gradle, NPM
- **Automated Agents**: Dependabot, code review bots, issue-to-PR generators

Each tool generates valuable insights, but this knowledge remains siloed. What if your IDE could learn from CI failures? What if your build system could suggest optimizations based on patterns across all projects?

## 🧠 The Solution: Unified Development Memory

Using Cognee's graph-based memory engine with Redis vector storage, we've created a system that:

1. **Tracks tool interactions** across multiple sources
2. **Organizes knowledge** by both source (who/what) and project (where)
3. **Enables cross-dimensional queries** to surface patterns and insights
4. **Maintains provenance** of every piece of knowledge

## 🏗️ Architecture & Ontology

### Core Entities

The system uses five key entity types:

**SourceNodeSet** - Categorizes WHO/WHAT is creating knowledge:
- IDE Sources: `ide_cursor`, `ide_vscode`, `ide_windsurf`, `ide_jetbrains`
- Agent Sources: `agent_github_actions`, `agent_dependabot`, `agent_code_review`, `agent_issue_to_pr`
- CI/CD Sources: `cicd_jenkins`, `cicd_github_actions`, `cicd_gitlab_ci`, `cicd_circleci`
- Build Sources: `build_docker`, `build_gradle`, `build_npm`

**ProjectNodeSet** - Organizes WHERE knowledge applies:
- Format: `project_{organization}_{repository}`
- Examples: `project_cognee_core`, `project_cognee_mcp`, `project_mycompany_backend`

**MCPToolCall** - Records WHAT happened:
- Links to: Developer, MCPTool, SourceNodeSet, ProjectNodeSet
- Tracks: parameters, results, timestamps, concepts mentioned
- Enables full provenance tracking of every interaction

**Developer** - WHO initiated the action
**Concept** - WHAT concepts were involved

### Memory Storage

The system uses **Redis** as the vector database, providing:
- Sub-millisecond query latency
- Horizontal scalability for team-wide deployments
- Persistent memory across tool restarts
- Efficient similarity searches for pattern matching

## 📊 MCP Tools & Example Queries

The system exposes several MCP tools that can be invoked through natural language in any MCP client:

### Core MCP Tools

**Memory Management:**
- **`cognify`** - Turn your data into a structured knowledge graph and store in memory
- **`codify`** - Analyze a code repository, build a code graph, store in memory
- **`search`** - Query memory with types: GRAPH_COMPLETION, RAG_COMPLETION, CODE, INSIGHTS, CHUNKS
- **`list_data`** - List all datasets and their data items with IDs
- **`delete`** - Delete specific data from a dataset (soft/hard deletion modes)
- **`prune`** - Reset cognee for a fresh start (removes all data)
- **`cognify_status` / `codify_status`** - Track pipeline progress

**Multi-Actor Tracking:**
- **`add_tool_call_event`** - Records tool interactions with full context
- **`get_tool_calls_by_source`** - Filter by source (IDE, CI/CD, etc.)
- **`get_tool_calls_by_project`** - Filter by project
- **`get_tool_calls_by_nodesets`** - Filter by both dimensions
- **`get_tool_calls_by_developer`** - Track individual activity
- **`get_all_tool_calls`** - Retrieve all recorded interactions

**Developer Rules:**
- **`add_developer_rules`** - Add custom development rules and patterns
- **`get_developer_rules`** - Retrieve stored rules and patterns
- **`save_interaction`** - Save important interactions for learning

### Example Natural Language Queries

**1. Cross-Project Pattern Analysis**

Ask your MCP client:
- *"Show me all CI/CD failures from GitHub Actions"*
- *"Search for CI failures with dependency conflicts using INSIGHTS"*
- *"Find common build failure patterns across all projects"*

**2. IDE-Specific Learning**

Ask your MCP client:
- *"Show Cursor activity in the backend project"*
- *"Search for TypeScript type errors in Cursor IDE using GRAPH_COMPLETION"*
- *"What issues do VS Code users commonly face?"*

**3. Build Optimization Insights**

Ask your MCP client:
- *"Show all Docker build activity"*
- *"Search for Docker layer caching improvements from successful builds using INSIGHTS"*
- *"What are the fastest build configurations used by the team?"*

## 🚀 Downstream Use Cases

### 1. **Predictive CI/CD Assistance**
- Warn developers about likely CI failures before pushing
- Suggest fixes based on historical patterns
- Auto-generate pre-commit hooks from common issues

### 2. **Cross-IDE Knowledge Transfer**
- Share coding patterns between team members using different IDEs
- Surface relevant snippets from other projects
- Standardize practices across diverse toolsets

### 3. **Intelligent Build Optimization**
- Recommend build configuration changes
- Identify redundant steps across projects
- Predict build times based on change patterns

### 4. **Automated Documentation**
- Generate runbooks from actual tool usage
- Create onboarding guides from common developer queries
- Maintain up-to-date troubleshooting guides

### 5. **Team Intelligence Dashboard**
- Visualize tool usage patterns
- Identify knowledge gaps
- Track learning curves for new team members

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Redis instance (for vector storage)
- OpenAI API key (or other LLM provider)

### Quick Installation

1. Install uv if you don't have it:
   ```bash
   pip install uv
   ```

2. Clone and navigate to the directory:
   ```bash
   cd experimental/multi-actor-mem-coding-agents
   ```

3. Install dependencies:
   ```bash
   uv sync --dev --all-extras
   ```

4. Set up your environment (.env file):
   ```bash
   LLM_API_KEY="YOUR_OPENAI_API_KEY"
   VECTOR_DB_PROVIDER="redis"
   REDIS_URL="redis://localhost:6379"
   ```

5. Run the MCP server:
   ```bash
   # With stdio transport (default)
   python src/server.py
   
   # With SSE transport (real-time streaming)
   python src/server.py --transport sse
   
   # With HTTP transport (recommended for web deployments)
   python src/server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp
   ```

### Using with Cursor IDE

1. Create a run script (`run-cognee.sh`):
   ```bash
   #!/bin/bash
   export TOKENIZERS_PARALLELISM=false
   export LLM_API_KEY=your-OpenAI-API-key
   cd /path/to/multi-actor-mem-coding-agents
   uv run python src/server.py
   ```

2. Configure Cursor (Settings → MCP Tools → New MCP Server):
   ```json
   {
     "mcpServers": {
       "cognee-multi-actor": {
         "command": "sh",
         "args": ["/path/to/run-cognee.sh"]
       }
     }
   }
   ```

3. Start using natural language queries in Cursor!

## 🐳 Docker Usage

For containerized deployments:

1. **Build locally**:
   ```bash
   docker build -t cognee/multi-actor-mcp:latest .
   ```

2. **Run with different transports**:
   ```bash
   # HTTP transport (recommended for web)
   docker run --env-file ./.env -p 8000:8000 --rm -it cognee/multi-actor-mcp:latest --transport http
   
   # SSE transport
   docker run --env-file ./.env -p 8000:8000 --rm -it cognee/multi-actor-mcp:latest --transport sse
   
   # stdio transport (default)
   docker run --env-file ./.env --rm -it cognee/multi-actor-mcp:latest
   ```

## 💻 How It Works in Practice

### Recording Tool Interactions

When a developer uses a tool in their IDE or CI/CD system, the interaction is automatically recorded with full context. For example, when using Cursor IDE to refactor a React component:

The system captures:
- **Source**: `ide_cursor` (which tool/actor)
- **Project**: `project_acme_frontend` (which codebase)
- **Tool**: `cognify` (what MCP tool was used)
- **Parameters**: File path, code content
- **Result**: Success/failure and what was learned
- **Concepts**: "React hooks optimization", "TypeScript generics"
- **Developer**: Who performed the action
- **Timestamp**: When it happened

### Querying Across Dimensions

Later, any developer can ask their MCP client:

**"Show me all React optimization patterns from any IDE"**
- The system searches across all IDEs for React-related patterns
- Returns insights from Cursor, VS Code, and other tools

**"What build issues affect the frontend project?"**
- Filters by both project (`project_acme_frontend`) and source type (`build_npm`)
- Shows specific build problems for that project

**"How do other teams handle authentication?"**
- Searches across all projects for authentication patterns
- Returns solutions from different teams and tools

## 🔮 Future Possibilities

### Immediate Innovations
1. **AI-Powered Code Reviews**: Use accumulated knowledge to provide context-aware review comments
2. **Dependency Impact Analysis**: Predict ripple effects of package updates across projects
3. **Team Skill Mapping**: Identify expertise based on tool usage patterns
4. **Automated Refactoring Suggestions**: Surface refactoring opportunities from cross-project patterns
5. **Security Pattern Detection**: Identify potential vulnerabilities based on historical issues

### Advanced Multi-Actor Intelligence
6. **Development Pattern Mining**: Discover implicit workflows that emerge from actual usage patterns
   - *"What tools are typically used together when implementing auth features?"*
   - *"Show me the typical workflow from feature request to deployment"*

7. **Cross-Agent Collaboration Tracking**: Monitor how different AI agents collaborate on tasks
   - Track when code generation agents work with test generation agents
   - Identify successful human-AI collaboration patterns
   - Optimize agent interactions based on historical success

8. **Temporal Workflow Discovery**: Understand time-based patterns in development flows
   - Which tools are used during "crunch time" vs normal development?
   - How do AI agent usage patterns differ from human patterns by time of day?
   - What's the typical sequence from feature request → implementation → deployment?

9. **Knowledge Transfer Mapping**: Connect developers through shared tool usage patterns
   - *"Which developers have worked on similar problems to what I'm facing?"*
   - *"Find experts in microservices architecture based on tool usage"*
   - *"Who should I ask about Redis optimization?"*

10. **Predictive Tool Suggestions**: Based on current context and historical patterns
    - "Developers working on similar components typically use these debugging tools next"
    - "When implementing this pattern, teams usually need these validation tools"

11. **AI Training Data Generation**: Extract successful patterns for training better AI assistants
    - *"Extract all successful refactoring patterns from senior developers"*
    - *"Show me high-quality code review patterns for training"*
    - *"Find examples of excellent error handling across projects"*

12. **Development Velocity Insights**: Correlate tool usage patterns with productivity metrics
    - Do certain tools reduce time spent on boilerplate tasks?
    - Which tool combinations lead to fewer bugs in production?
    - How do AI agents affect overall development velocity?

### Organizational Intelligence
13. **Multi-Project Cross-Pollination**: Learn from patterns across entire organization
    - *"How do different projects handle database migrations?"*
    - *"Show me authentication patterns across all microservices"*
    - *"What testing strategies work best for React applications?"*

14. **Security Audit Trails**: Comprehensive tracking of who accessed what tools when
    - *"Show all database admin tool usage in production projects"*
    - *"Track sensitive operations in the fintech project"*
    - *"Alert on unusual access patterns"*

15. **Automated Workflow Generation**: Create GitHub Actions, IDE macros from successful patterns
    - "Teams that successfully implement feature X typically use this CI/CD pipeline"
    - "Generate IDE snippets based on most commonly successful code patterns"

16. **Development Health Metrics**: Organizational insights for team leads
    - Are junior developers using debugging tools excessively? (mentoring opportunity)
    - Are senior developers avoiding new tools? (training need)
    - Are AI agents creating technical debt? (code quality tracking)

## 🎨 Visualization & Analytics Ideas

### Real-Time Dashboards
1. **Actor Interaction Networks**: Graph showing how humans, AI agents, and systems interact through shared tool usage
2. **Temporal Heat Maps**: Visualize when different actors are most active and what tools they prefer at different times
3. **Knowledge Flow Diagrams**: Show how information moves from documentation → human exploration → AI implementation → CI/CD validation
4. **Tool Evolution Timelines**: Track how tool preferences change over time as new technologies emerge

### Advanced Analytics
5. **Development Velocity Correlation Matrix**: Compare tool usage patterns with code quality metrics, bug rates, and delivery speed
6. **Cross-Project Similarity Clustering**: Group projects by their tool usage DNA to identify reusable patterns
7. **AI vs Human Behavioral Analysis**: Understand the different approaches taken by artificial and human actors
8. **Temporal Workflow Sequences**: Visualize the typical tool chains used for different types of work

### Example Queries for Visualization

Ask your MCP client to generate visualization data:

- *"Show all tool interactions between humans and AI agents in the last month"*
- *"Get all tool calls grouped by time of day and source type"*
- *"Compare tool usage patterns between frontend, backend, and mobile projects"*
- *"Show me collaboration patterns between different actor types"*

## 🔐 Privacy & Security Framework

### Multi-Tenant Architecture
- **Project Isolation**: NodeSets can enforce strict boundaries between different projects/teams
- **Role-Based Access**: Different query permissions based on developer roles and project access
- **Anonymization Options**: Hash developer IDs for privacy while maintaining relationship data

### Audit & Compliance
- **Query Audit Trails**: Track who queries what information about tool usage patterns
- **Data Retention Policies**: Configurable retention based on data sensitivity and regulatory requirements
- **Consent Management**: Developers can opt-out of certain types of tracking while maintaining team insights

### Security Use Cases

Ask your MCP client for security insights:

- *"Search for tool calls from unauthorized sources in production projects"*
- *"Find database admin function usage by non-admin users"*
- *"Show GitHub Actions activity in the fintech core project"*
- *"Track compliance violations in regulated projects"*



