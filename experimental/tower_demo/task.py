import os
import asyncio
import json
import pathlib
from datetime import datetime
from typing import Dict, Any, List
import time

import requests
import pyarrow as pa


try:
    import tower

    TOWER_AVAILABLE = True
except ImportError:
    TOWER_AVAILABLE = False
    print("⚠️ Tower SDK not available - Iceberg functionality will be disabled")

import cognee
from cognee import visualize_graph
from cognee.shared.logging_utils import get_logger, ERROR
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
HN_API_BASE = os.getenv("HN_API_BASE", "https://hacker-news.firebaseio.com/v0")
MAX_STORIES = int(os.getenv("MAX_STORIES", "30"))
TOWER_ENV = os.getenv("TOWER_ENVIRONMENT", "local")


# LLM Configuration for Cognee
def setup_llm_config():
    """Setup LLM configuration for Cognee using Tower secrets"""
    # Try to get API keys from environment (Tower injects secrets as env vars)
    openai_key = os.getenv("LLM_API_KEY")

    if openai_key:
        print("🔑 Using LLM_API_KEY key from Tower secrets")
        os.environ["LLM_API_KEY"] = openai_key
        # Configure Cognee to use OpenAI
        cognee.config.llm_api_key = openai_key
        cognee.config.llm_model = "gpt-4o-mini"
    else:
        print("⚠️ Please set OpenAI key as LLM_API_KEY in Tower secrets")
        return False

    return True


# Iceberg table schema for Hacker News stories
HACKERNEWS_SCHEMA = pa.schema(
    [
        pa.field("id", pa.int64()),
        pa.field("title", pa.string()),
        pa.field("text", pa.string()),
        pa.field("url", pa.string()),
        pa.field("by", pa.string()),
        pa.field("score", pa.int32()),
        pa.field("time", pa.int64()),
        pa.field("type", pa.string()),
        pa.field("descendants", pa.int64()),
        pa.field("parent", pa.int64()),
        pa.field("deleted", pa.bool_()),
        pa.field("dead", pa.bool_()),
        pa.field("poll", pa.int64()),
        pa.field("kids", pa.list_(pa.int64())),
        pa.field("parts", pa.list_(pa.int64())),
    ]
)

SEARCH_RESULTS_SCHEMA = pa.schema(
    [
        pa.field("search_id", pa.string()),
        pa.field("query", pa.string()),
        pa.field("result", pa.string()),
        pa.field("timestamp", pa.string()),
        pa.field("articles_count", pa.int32()),
        pa.field("dataset_name", pa.string()),
    ]
)


class HackerNewsProcessor:
    """Handles Hacker News data extraction and processing"""

    def __init__(self):
        self.api_base = HN_API_BASE
        self.max_stories = MAX_STORIES

    def fetch_story_data(self, story_id: int) -> Dict[str, Any]:
        """Fetch individual story data from HN API"""
        try:
            response = requests.get(f"{self.api_base}/item/{story_id}.json")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"⚠️ Error fetching story {story_id}: {e}")
        return None

    def process_stories(self, last_timestamp: int = 0) -> List[Dict[str, Any]]:
        """Extract and process Hacker News stories"""
        print(f"📡 Extracting data from Hacker News API...")
        print(f"   API Base: {self.api_base}")
        print(f"   Max Stories: {self.max_stories}")
        print(f"   Last timestamp: {last_timestamp}")

        # Get top stories
        try:
            response = requests.get(f"{self.api_base}/topstories.json")
            story_ids = response.json()[: self.max_stories]
            print(f"🔍 Processing {len(story_ids)} top stories")
        except Exception as e:
            print(f"❌ Failed to fetch story IDs: {e}")
            return []

        stories = []
        processed_count = 0
        new_stories_count = 0

        for story_id in story_ids:
            story_data = self.fetch_story_data(story_id)

            if story_data and story_data.get("type") == "story":
                story_time = story_data.get("time", 0)

                if story_time > last_timestamp:
                    stories.append(story_data)
                    new_stories_count += 1

            processed_count += 1
            if processed_count % 10 == 0:
                print(f"   Processed {processed_count} stories, found {new_stories_count} new ones")

            time.sleep(0.1)  # Rate limiting

        print(f"✅ Finished processing. Total new stories: {new_stories_count}")
        return stories

    def write_to_iceberg(self, stories: List[Dict[str, Any]]) -> bool:
        """Write stories to Iceberg table using Tower"""
        if not TOWER_AVAILABLE:
            print("❌ Tower SDK not available - cannot write to Iceberg")
            return False

        if not stories:
            print("❌ No stories to write to Iceberg")
            return False

        print(f"\n💾 Storing {len(stories)} stories in Iceberg table...")
        print(f"🔧 Debug: Tower environment = {TOWER_ENV}")

        try:
            # Create or get Iceberg table
            table_name = (
                "hn_stories_v1"  # This will be used in the next step to read from the table
            )
            namespace = "hn_v1"  # This will be used in the next step to read from the table
            print(
                f"🔧 Debug: Creating table reference for '{table_name}' in namespace '{namespace}'"
            )
            table_ref = tower.tables(table_name, namespace=namespace)
            print(f"🔧 Debug: Table reference created, now calling create_if_not_exists...")
            table = table_ref.create_if_not_exists(HACKERNEWS_SCHEMA)
            print(f"🔧 Debug: Table created/loaded successfully")

            # Get the expected field names from schema
            schema_field_names = {field.name for field in HACKERNEWS_SCHEMA}
            print(f"🔧 Debug: Expected schema fields: {sorted(schema_field_names)}")

            # Convert stories to PyArrow format and write to table
            records = []
            for story in stories:
                record = {}
                for field in HACKERNEWS_SCHEMA:
                    field_name = field.name

                    # Retrieve from original story dict
                    value = story.get(field_name, None)

                    # Handle specific field types and provide defaults if missing
                    if field_name in ["kids", "parts"]:
                        # Ensure lists are properly formatted
                        if value is None:
                            value = []
                        elif not isinstance(value, list):
                            value = []
                        # Ensure all elements are integers
                        value = [int(x) for x in value if x is not None]
                    elif value is None:
                        if pa.types.is_string(field.type):
                            value = ""
                        elif pa.types.is_integer(field.type):
                            value = 0
                        elif pa.types.is_boolean(field.type):
                            value = False
                        elif pa.types.is_list(field.type):
                            value = []

                    record[field_name] = value

                records.append(record)

            # Debug: Check the first record structure
            if records:
                print(f"🔧 Debug: First record keys: {sorted(records[0].keys())}")
                print(f"🔧 Debug: Sample kids value: {records[0].get('kids', 'NOT_FOUND')}")
                print(f"🔧 Debug: Sample parts value: {records[0].get('parts', 'NOT_FOUND')}")

            # Create PyArrow Table and write
            # Use from_pylist for list of dictionaries with explicit schema
            pa_table = pa.Table.from_pylist(records, schema=HACKERNEWS_SCHEMA)
            print(f"🔧 Debug: Writing {len(records)} records to table...")

            # Insert data into the table
            table.insert(pa_table)

            print(f"✅ Stored {len(records)} stories in Iceberg table")
            return True

        except Exception as e:
            import traceback

            print(f"⚠️ Iceberg storage failed: {e}")
            print(f"🔧 Debug: Full error traceback:")
            traceback.print_exc()

            # Provide specific guidance for common issues
            error_message = str(e)
            if "Expecting value" in error_message or "JSON" in error_message:
                print("\n💡 JSON parsing error suggests:")
                print("   1. Check Snowflake Open Catalog permissions")
                print("   2. Verify catalog URI and credentials in Tower")
                print("   3. Ensure catalog role has CATALOG_MANAGE_CONTENT privilege")
                print("   4. Check if catalog role is granted to principal role")

            return False

    def read_from_iceberg(self) -> List[Dict[str, Any]]:
        """Read articles back from Iceberg table using Tower"""
        if not TOWER_AVAILABLE:
            print("❌ Tower SDK not available - cannot read from Iceberg")
            return []

        try:
            print("📖 Reading data back from Iceberg table...")

            # Get Iceberg table we created in the previous step
            table_name = "hn_stories_v1"
            namespace = "hn_v1"
            table_ref = tower.tables(table_name, namespace=namespace)

            # Read all data from the table (returns Polars LazyFrame)
            df = table_ref.load().to_polars()

            # Collect LazyFrame to DataFrame, then convert to list of dictionaries
            stories = df.collect().to_dicts()

            print(f"✅ Successfully read {len(stories)} stories from Iceberg table")
            return stories

        except Exception as e:
            import traceback

            print(f"⚠️ Failed to read from Iceberg: {e}")
            print(f"🔧 Debug: Full error traceback:")
            traceback.print_exc()
            return []

    def stories_to_cognee_content(self, stories: List[Dict[str, Any]]) -> str:
        """Convert all story fields to flat text format for Cognee processing"""

        content_parts = ["# Hacker News Stories from Iceberg - All Fields Dataset\n\n"]

        for story in stories:
            story_text = f"## Story ID: {story.get('id', 'Unknown')}\n\n"

            # Process all fields in the story
            for key, value in story.items():
                if value is not None and value != "" and value != [] and value != 0:
                    # Handle different data types
                    if isinstance(value, list):
                        if value:  # Only include non-empty lists
                            story_text += f"**{key}:** {', '.join(map(str, value))}\n"
                    elif isinstance(value, (int, float)):
                        if value > 0:  # Only include meaningful numbers
                            story_text += f"**{key}:** {value}\n"
                    else:
                        story_text += f"**{key}:** {value}\n"

            story_text += "\n---\n\n"
            content_parts.append(story_text)

        return "\n".join(content_parts)


class CogneeProcessor:
    """Handles Cognee knowledge graph processing"""

    def __init__(self):
        self.setup_directories()

    def setup_directories(self):
        """Setup Cognee directories and database configuration"""
        current_dir = pathlib.Path(__file__).parent

        self.data_directory = str(current_dir / "data_storage")
        self.cognee_directory = str(current_dir / "cognee_system")

        # Configure graph database provider
        cognee.config.set_graph_db_config(
            {
                "graph_database_provider": "networkx",  # You can change this to other providers like "kuzu", "neo4j", etc.
            }
        )
        cognee.config.set_vector_db_config(
            {
                "vector_db_provider": "lancedb",  # Specify lancedb as provider
            }
        )
        cognee.config.set_relational_db_config(
            {
                "db_provider": "sqlite",  # Specify SQLite as provider
            }
        )

        cognee.config.data_root_directory(self.data_directory)
        cognee.config.system_root_directory(self.cognee_directory)

        print(f"🔧 Cognee configured:")
        print(f"   Data directory: {self.data_directory}")
        print(f"   System directory: {self.cognee_directory}")

    async def process_stories_with_cognee(self, stories: List[Dict[str, Any]]) -> str:
        """Process stories through Cognee to build knowledge graph"""

        if not stories:
            print("❌ No stories to process with Cognee")
            return None

        print(f"🧠 Processing {len(stories)} stories with Cognee...")

        # Clean previous data
        print("🧹 Cleaning previous Cognee data...")
        try:
            await cognee.prune.prune_data()
            await cognee.prune.prune_system(metadata=True)
        except Exception as e:
            print(f"⚠️ Warning during cleanup: {e}")

        # Prepare stories for cognification
        hn_processor = HackerNewsProcessor()
        content = hn_processor.stories_to_cognee_content(stories)

        # Optional: Save content for reference
        content_file = "hn_stories_to_cognee.txt"
        with open(content_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📄 Saved content to {content_file}")

        # Process with Cognee
        dataset_name = "hn_stores"

        try:
            print("📊 Adding content to Cognee...")
            await cognee.add([content], dataset_name)

            print("🧠 Building knowledge graph...")
            await cognee.cognify([dataset_name])

            print("🔍 Visualizing knowledge graph...")
            # Save graph visualization to current working directory to for local testing
            current_dir = pathlib.Path.cwd()
            graph_file_path = str(current_dir / "graph_visualization.html")
            await visualize_graph(graph_file_path)

            print(f"✅ Knowledge graph construction completed!")
            print(f"📊 Graph visualization saved to: {graph_file_path}")
            return dataset_name

        except Exception as e:
            print(f"❌ Cognee processing failed: {e}")
            return None

    async def search_knowledge_graph(self, queries: List[str]) -> Dict[str, Any]:
        """Search the knowledge graph with multiple queries"""
        results = {}

        print(f"\n🔍 Running {len(queries)} knowledge graph searches...")

        for i, query in enumerate(queries, 1):
            print(f"\n📝 Query {i}/{len(queries)}: '{query}'")

            try:
                result = await cognee.search(query)
                results[query] = str(result)

                print("📊 Result preview:")
                print("=" * 50)
                # Truncate long results for display
                result_preview = (
                    str(result)[:300] + "..." if len(str(result)) > 300 else str(result)
                )
                print(result_preview)
                print("=" * 50)

            except Exception as e:
                print(f"❌ Search error: {e}")
                results[query] = f"Error: {e}"

            await asyncio.sleep(0.5)  # Brief pause between searches

        return results

    def store_search_results_in_iceberg(
        self, search_results: Dict[str, str], dataset_name: str, articles_count: int
    ) -> bool:
        """Store search results in a separate Iceberg table"""
        if not TOWER_AVAILABLE:
            print("❌ Tower SDK not available - skipping search results storage")
            return False

        try:
            print(f"💾 Storing {len(search_results)} search results in Iceberg...")

            # Create or get search results Iceberg table
            table_name = "cognee_search_results_v1"
            namespace = "cognee_search_results_v1"
            table_ref = tower.tables(table_name, namespace=namespace)
            table = table_ref.create_if_not_exists(SEARCH_RESULTS_SCHEMA)

            # Convert search results to records
            records = []
            timestamp = datetime.now().isoformat()

            for i, (query, result) in enumerate(search_results.items(), 1):
                record = {
                    "search_id": f"search_{timestamp}_{i}",
                    "query": query,
                    "result": result,
                    "timestamp": timestamp,
                    "articles_count": articles_count,
                    "dataset_name": dataset_name,
                }
                records.append(record)

            # Create PyArrow table and insert
            pa_table = pa.Table.from_pylist(records, schema=SEARCH_RESULTS_SCHEMA)
            table.insert(pa_table)

            print(
                f"✅ Successfully stored {len(records)} search results in Iceberg table: {namespace}.{table_name}"
            )
            return True

        except Exception as e:
            import traceback

            print(f"⚠️ Search results storage failed: {e}")
            print(f"🔧 Debug: Full error traceback:")
            traceback.print_exc()
            return False


async def main():
    """Main integrated pipeline execution"""

    print("🚀 Tower Cognee Demo Hacker News Pipeline")
    print("=" * 70)
    print(f"🔧 Running in {TOWER_ENV} environment")

    try:
        # Setup LLM configuration
        print("\n🔑 Setting up LLM configuration...")
        if not setup_llm_config():
            print("❌ LLM configuration failed. Please set up API keys in Tower secrets.")
            return 1

        # Initialize processors
        hn_processor = HackerNewsProcessor()
        cognee_processor = CogneeProcessor()

        # Step 1: Fetch HN data
        print("\n📡 Step 1: Fetching Hacker News data...")
        stories = hn_processor.process_stories()
        if not stories:
            print("❌ No stories extracted. Exiting.")
            return 1

        # Step 2: Write to Iceberg
        print(f"\n💾 Step 2: Writing {len(stories)} stories to Iceberg...")
        if TOWER_AVAILABLE:
            iceberg_write_success = hn_processor.write_to_iceberg(stories)
            if not iceberg_write_success:
                print("⚠️ Iceberg write failed, continuing with original data...")
        else:
            print("⚠️ Tower SDK not available - skipping Iceberg write")
            iceberg_write_success = False

        # Step 3: Read from Iceberg
        print("\n📖 Step 3: Reading data from Iceberg...")
        if TOWER_AVAILABLE:
            iceberg_stories = hn_processor.read_from_iceberg()
            if not iceberg_stories:
                print("⚠️ Iceberg read failed, using original data...")
                iceberg_stories = stories
        else:
            print("⚠️ Tower SDK not available - using original data")
            iceberg_stories = stories

        # Step 4: Cognify
        print("\n🧠 Step 4: Processing with Cognee...")
        dataset_name = await cognee_processor.process_stories_with_cognee(iceberg_stories)
        if not dataset_name:
            print("❌ Cognee processing failed")
            return 1

        # Step 5: Search
        print("\n🔍 Step 5: Searching knowledge graph...")
        example_queries = [
            "What are the main technology topics discussed in these Hacker News stories?",
            "Which companies or organizations are mentioned most frequently?",
        ]
        search_results = await cognee_processor.search_knowledge_graph(example_queries)

        # Step 6: Write search output back to Iceberg
        print("\n💾 Step 6: Writing search results to Iceberg...")
        if TOWER_AVAILABLE:
            search_storage_success = cognee_processor.store_search_results_in_iceberg(
                search_results, dataset_name, len(iceberg_stories)
            )
        else:
            print("⚠️ Tower SDK not available - skipping search results storage")
            search_storage_success = False

        # Generate summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "environment": TOWER_ENV,
            "total_stories_processed": len(iceberg_stories),
            "cognee_dataset": dataset_name,
            "knowledge_graph_searches": len(search_results),
            "search_results": search_results,
        }

        # Save summary
        summary_file = "tower_integration_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"\n✅ Pipeline completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Stories processed: {len(iceberg_stories)}")
        print(f"   - Knowledge graph dataset: {dataset_name}")
        print(f"   - Knowledge searches: {len(search_results)}")
        print(f"   - Summary saved to: {summary_file}")
        print(f"   - Graph visualization: ./graph_visualization.html")

        return 0

    except Exception as e:
        print(f"❌ Pipeline failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    logger = get_logger(level=ERROR)

    # Run the integrated pipeline
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        exit(1)
