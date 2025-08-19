import asyncio
import os
import pathlib
import cognee
from cognee.modules.search.types import SearchType
from cognee.modules.engine.models import NodeSet
from openai import OpenAI

async def main():
    # Configure cognee directories to match the setup from docs_intelligence_cognee.py
    current_dir = pathlib.Path(__file__).parent
    data_directory_path = str(current_dir / "data_storage")
    cognee.config.data_root_directory(data_directory_path)

    cognee_directory_path = str(current_dir / "cognee_system")
    cognee.config.system_root_directory(cognee_directory_path)

    query_text = "give me the list of all the subtopics of docker? if there is no docker subtopic say 'no subtopics found'"

    # Graph completion with NodeSet filtering
    graph_completion_node_set_answer = await cognee.search(
        query_type=SearchType.GRAPH_COMPLETION, 
        query_text=query_text, 
        node_type=NodeSet,
        node_name=["Aura_NodeSet"],
    )
    print("\nGraph completion answer with NodeSet filtering: (We expect to see no subtopics found)")
    for result in graph_completion_node_set_answer:
        print(f"- {result}")

    # Graph completion
    graph_completion_answer = await cognee.search(
        query_type=SearchType.GRAPH_COMPLETION, 
        query_text=query_text,
        top_k=15,
    )
    print("\nGraph completion answer:")
    for result in graph_completion_answer:
        print(f"- {result}")

    # Traditional RAG completion
    search_results_traditional_rag = await cognee.search(
        query_type=SearchType.RAG_COMPLETION,
        query_text=query_text,
    )
    print("\nTraditional RAG completion answer:")
    print(search_results_traditional_rag)

    # OpenAI completion
    os.environ["OPENAI_API_KEY"] = os.environ["LLM_API_KEY"]
    client = OpenAI()
    
    llm_response = client.responses.create(
        model="gpt-4o-mini",
        input=query_text
    )
    
    print("\nOpenAI response:")
    print(llm_response.output_text)


if __name__ == "__main__":
    asyncio.run(main())
