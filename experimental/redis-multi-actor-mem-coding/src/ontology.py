from __future__ import annotations
import uuid
from typing import List, Optional, Dict, Any, Literal
from cognee.low_level import DataPoint
from cognee.modules.engine.models import NodeSet

def create_unique_id(text: str) -> str:
    """Creates a unique id for a given text."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))

# Define allowed source types
SourceType = Literal[
    # IDE Sources
    "ide_cursor",
    "ide_windsurf",
    "ide_vscode",
    "ide_jetbrains",
    # Agent Sources
    "agent_github_actions",
    "agent_issue_to_pr",
    "agent_dependabot", 
    "agent_code_review",
    # CI/CD/Build Sources
    "cicd_jenkins",
    "cicd_github_actions",
    "cicd_gitlab_ci",
    "cicd_circleci",
    "build_docker",
    "build_gradle",
    "build_npm",
]

def validate_source_nodeset(source: str) -> bool:
    """Validate if the source nodeset name is allowed."""
    allowed_sources = {
        "ide_cursor", "ide_windsurf", "ide_vscode", "ide_jetbrains",
        "agent_github_actions", "agent_issue_to_pr", "agent_dependabot", "agent_code_review",
        "cicd_jenkins", "cicd_github_actions", "cicd_gitlab_ci", "cicd_circleci",
        "build_docker", "build_gradle", "build_npm"
    }
    return source in allowed_sources

def validate_project_nodeset(project: str) -> bool:
    """Validate if the project nodeset name follows the correct format."""
    return project.startswith("project_") and len(project) > 8

class SourceNodeSet(DataPoint):
    """Source/Actor nodeset for categorizing where interactions come from."""
    nodeset_id: str
    name: SourceType
    category: Literal["ide", "agent", "cicd", "build"]
    metadata: Dict[str, Any] = {"index_fields": ["name", "category"], "embed_fields": []}

class ProjectNodeSet(DataPoint):
    """Project/Repository nodeset for organizing by codebase."""
    nodeset_id: str  
    name: str  # e.g., "project_cognee_mcp"
    organization: str  # e.g., "cognee"
    repository: str  # e.g., "mcp"
    metadata: Dict[str, Any] = {"index_fields": ["name", "organization", "repository"], "embed_fields": []}

class MCPServer(DataPoint):
    """FastMCP / MCP server instance that exposes tools."""
    server_id: str
    name: str
    version: str
    transport: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    tools: List[MCPTool] = []
    metadata: Dict[str, Any] = {"index_fields": ["name", "server_id", "version"], "embed_fields": []}

class MCPTool(DataPoint):
    """Tool/function exposed by a server."""
    tool_id: str
    name: str
    signature: str
    docstring: str
    language: Optional[str] = None
    returns: Optional[str] = None
    hosted_by: Optional[MCPServer] = None
    metadata: Dict[str, Any] = {"index_fields": ["name", "docstring", "tool_id"], "embed_fields": ["docstring"]}

class Developer(DataPoint):
    """Human or bot actor."""
    dev_id: str
    name: str
    role: Optional[str] = None
    metadata: Dict[str, Any] = {"index_fields": ["name", "dev_id", "role"], "embed_fields": []}

class Concept(DataPoint):
    """Abstract/domain concept."""
    concept_id: str
    description: str
    tags: List[str] = []
    metadata: Dict[str, Any] = {"index_fields": ["description"], "embed_fields": ["description"]}

class MCPToolCall(DataPoint):
    """Concrete invocation of a tool (provenance)."""
    call_id: str
    timestamp: str
    parameters: Dict[str, Any]
    result_digest: str
    call_of: MCPTool
    called_by: Developer
    mentions: List[Concept] = []
    source_nodeset: Optional[SourceNodeSet] = None
    project_nodeset: Optional[ProjectNodeSet] = None
    metadata: Dict[str, Any] = {"index_fields": ["call_id", "timestamp"], "embed_fields": []} 