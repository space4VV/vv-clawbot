"""RAG (Retrieval Augmented Generation) module."""

import re
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import settings
from ..logger import get_logger
from ..models import RagDocument, RetrieveResult

logger = get_logger("rag")


class RagClient:
    """RAG client for semantic search."""

    def __init__(self) -> None:
        self._client = None
        self._collection = None

    @property
    def client(self) -> chromadb.Client:
        """Get the ChromaDB client."""
        if self._client is None:
            db_path = Path(settings.rag.vector_db_path)
            db_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(db_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    async def initialize(self) -> None:
        """Initialize the vector store."""
        logger.info("Initializing RAG system...")

        # Get or create collection
        self._collection = self.client.get_or_create_collection(
            name="slack_messages",
            metadata={"description": "Indexed Slack messages"},
        )

        logger.info(f"RAG initialized with {self._collection.count()} documents")

    async def add_documents(
        self,
        documents: list[dict[str, str]],
        ids: list[str],
    ) -> None:
        """Add documents to the vector store.

        Args:
            documents: List of document dicts with 'content', 'channel_name', 'user_name', 'ts'
            ids: List of document IDs
        """
        if not self._collection:
            await self.initialize()

        contents = [doc["content"] for doc in documents]
        metadatas = [
            {
                "channel_name": doc.get("channel_name"),
                "user_name": doc.get("user_name"),
                "ts": doc.get("ts"),
            }
            for doc in documents
        ]

        self._collection.add(
            documents=contents,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"Added {len(documents)} documents to RAG")

    async def search(
        self,
        query: str,
        limit: int = 10,
        channel_name: str | None = None,
        min_score: float = 0.5,
    ) -> list[RagDocument]:
        """Search for relevant documents.

        Args:
            query: Search query
            limit: Maximum number of results
            channel_name: Optional channel filter
            min_score: Minimum similarity score

        Returns:
            List of relevant documents
        """
        if not self._collection:
            await self.initialize()

        # Build where clause for filtering
        where = None
        if channel_name:
            where = {"channel_name": channel_name}

        results = self._collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,
        )

        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance  # Convert distance to similarity

                if score >= min_score:
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    documents.append(
                        RagDocument(
                            id=results["ids"][0][i],
                            content=doc,
                            channel_name=metadata.get("channel_name"),
                            user_name=metadata.get("user_name"),
                            ts=metadata.get("ts"),
                            score=score,
                        )
                    )

        return documents

    async def get_document_count(self) -> int:
        """Get the number of documents in the vector store."""
        if not self._collection:
            await self.initialize()
        return self._collection.count()

    async def delete_collection(self) -> None:
        """Delete the collection."""
        if self._client:
            self.client.delete_collection("slack_messages")
            logger.info("RAG collection deleted")


async def initialize_vector_store() -> None:
    """Initialize the vector store."""
    global _rag_client
    _rag_client = RagClient()
    await _rag_client.initialize()


async def retrieve(
    query: str,
    limit: int = 10,
    channel_name: str | None = None,
    min_score: float = 0.5,
) -> RetrieveResult:
    """Retrieve relevant documents for a query."""
    if not _rag_client:
        await initialize_vector_store()

    results = await _rag_client.search(
        query=query,
        limit=limit,
        channel_name=channel_name,
        min_score=min_score,
    )
    return RetrieveResult(results=results)


def should_use_rag(query: str) -> bool:
    """Determine if RAG should be used for a query.

    Args:
        query: User query

    Returns:
        True if RAG should be used
    """
    # RAG trigger keywords
    rag_keywords = [
        "what was",
        "discussed",
        "said earlier",
        "remember",
        "past",
        "previous",
        "history",
        "earlier",
        "before",
        "ago",
        "last week",
        "yesterday",
        "meeting",
        "decision",
    ]

    query_lower = query.lower()
    return any(keyword in query_lower for keyword in rag_keywords)


def build_context_string(results: list[RagDocument]) -> str:
    """Build a context string from retrieval results."""
    if not results:
        return ""

    lines = ["Relevant messages from Slack history:"]
    for i, doc in enumerate(results, 1):
        source = f"#{doc.channel_name}" if doc.channel_name else "unknown"
        if doc.user_name:
            source += f" by {doc.user_name}"
        lines.append(f"{i}. [{source}] {doc.content}")

    return "\n".join(lines)


def parse_query_filters(query: str) -> dict[str, str | None]:
    """Parse channel filters from query.

    Args:
        query: User query

    Returns:
        Dict with parsed filters
    """
    # Look for channel mentions like #channel-name
    channel_match = re.search(r"#(\w+)", query)

    return {
        "channel_name": channel_match.group(1) if channel_match else None,
    }


async def get_document_count() -> int:
    """Get the number of indexed documents."""
    if not _rag_client:
        await initialize_vector_store()
    return await _rag_client.get_document_count()


# Global client
_rag_client: RagClient | None = None

# Indexer state
_indexer_running = False


def start_indexer() -> None:
    """Start the background indexer."""
    global _indexer_running
    _indexer_running = True
    logger.info("Background indexer started")


def stop_indexer() -> None:
    """Stop the background indexer."""
    global _indexer_running
    _indexer_running = False
    logger.info("Background indexer stopped")


# Aliases
startIndexer = start_indexer
stopIndexer = stop_indexer
getDocumentCount = get_document_count
