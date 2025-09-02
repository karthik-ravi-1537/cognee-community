import os
import asyncio
import pathlib
import cognee

from cognee.shared.logging_utils import setup_logging, INFO

import cognee

node_set_aura = ["Aura_NodeSet"]
node_set_self_managed = ["Self-managed_NodeSet"]
node_set_docker = ["Docker_NodeSet", "Self-managed_NodeSet"]


async def main():
    current_dir = pathlib.Path(__file__).parent
    data_directory_path = str(current_dir / "data_storage")
    cognee.config.data_root_directory(data_directory_path)

    cognee_directory_path = str(current_dir / "cognee_system")
    cognee.config.system_root_directory(cognee_directory_path)

    # 1) Clean slate
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    # 3) Load the aura .md file
    aura_docs_path = current_dir / "neo4j_docs_aura.md"  # Adjust if needed
    if not aura_docs_path.exists():
        raise FileNotFoundError(f"Could not find {aura_docs_path}")

    with open(aura_docs_path, "r", encoding="utf-8") as f:
        aura_docs_content = f.read()

    # 4) Add the aura .md content to cognee
    await cognee.add([aura_docs_content], node_set=node_set_aura)

    # 5) Load the self-managed .md file
    self_managed_docs_path = current_dir / "neo4j_docs_operations_manual.md"  # Adjust if needed
    if not self_managed_docs_path.exists():
        raise FileNotFoundError(f"Could not find {self_managed_docs_path}")

    with open(self_managed_docs_path, "r", encoding="utf-8") as f:
        self_managed_docs_content = f.read()

    # 6) Add the self-managed .md content to cognee
    await cognee.add([self_managed_docs_content], node_set=node_set_self_managed)

    # 7) Load the modelling designs .md file
    docker_docs_path = current_dir / "neo4j_docs_operations_manual_docker.md"  # Adjust if needed
    if not docker_docs_path.exists():
        raise FileNotFoundError(f"Could not find {docker_docs_path}")

    with open(docker_docs_path, "r", encoding="utf-8") as f:
        docker_docs_content = f.read()

    # 8) Add the general .md content to cognee
    await cognee.add([docker_docs_content], node_set=node_set_docker)

    ontology_file_path = current_dir / "neo4j_docs_ontology.owl"
    if not ontology_file_path.exists():
        raise FileNotFoundError(f"Could not find {ontology_file_path}")

    # 9) "Cognify" the data to build out the knowledge graph
    await cognee.cognify(ontology_file_path=ontology_file_path)


if __name__ == "__main__":
    logger = setup_logging(log_level=INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
