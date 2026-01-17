# app/services/embedding_service.py
from typing import Any, Dict, List, Optional, Union, Tuple
import openai
import numpy as np
from numpy.typing import NDArray
import logging
from functools import lru_cache
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import backoff

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating and managing text embeddings using OpenAI's API.
    Supports batch processing, caching, and similarity calculations.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
        max_retries: int = 3,
        cache_size: int = 1000
    ):
        """
        Initialize the EmbeddingService.
        
        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY environment variable if None)
            model: Embedding model to use
            batch_size: Number of texts to process in a single API call
            max_retries: Maximum number of retries for API calls
            cache_size: Maximum number of embeddings to cache
        """
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        
        # Model dimensions for different models
        self.model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        
        # Initialize cache
        self._cache = {}
        self.cache_size = cache_size
    
    @property
    def embedding_dimension(self) -> int:
        """Get the embedding dimension for the current model."""
        return self.model_dimensions.get(self.model, 1536)
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _get_embeddings_with_retry(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Get embeddings with retry logic.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            
            # Sort embeddings in the order of input texts
            embeddings = [None] * len(texts)
            for data in response.data:
                embeddings[data.index] = data.embedding
            
            return embeddings
            
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            raise
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting embeddings: {e}")
            raise
    
    async def encode(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        use_cache: bool = True
    ) -> Union[NDArray[np.float32], List[NDArray[np.float32]]]:
        """
        Encode text(s) into embedding vectors.
        
        Args:
            texts: Single text string or list of texts
            normalize: Whether to normalize embeddings to unit length
            use_cache: Whether to use caching
            
        Returns:
            Single embedding array or list of embedding arrays
        """
        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]
        
        # Check cache for any cached embeddings
        embeddings = []
        texts_to_encode = []
        text_indices = []
        
        if use_cache:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    embeddings.append(self._cache[cache_key])
                else:
                    texts_to_encode.append(text)
                    text_indices.append(i)
                    # Initialize placeholder for this embedding
                    embeddings.append(None)
        else:
            texts_to_encode = texts
            text_indices = list(range(len(texts)))
            embeddings = [None] * len(texts)
        
        # Encode remaining texts in batches
        if texts_to_encode:
            for i in range(0, len(texts_to_encode), self.batch_size):
                batch_texts = texts_to_encode[i:i + self.batch_size]
                batch_indices = text_indices[i:i + self.batch_size]
                
                try:
                    batch_embeddings = await self._get_embeddings_with_retry(batch_texts)
                    
                    # Store in cache and results
                    for idx, emb, text in zip(batch_indices, batch_embeddings, batch_texts):
                        emb_array = np.array(emb, dtype=np.float32)
                        
                        if normalize:
                            emb_array = self.normalize(emb_array)
                        
                        # Store in cache
                        if use_cache:
                            cache_key = self._get_cache_key(text)
                            self._cache[cache_key] = emb_array
                            
                            # Manage cache size
                            if len(self._cache) > self.cache_size:
                                # Remove oldest entry (simple FIFO)
                                oldest_key = next(iter(self._cache))
                                del self._cache[oldest_key]
                        
                        embeddings[idx] = emb_array
                        
                except Exception as e:
                    logger.error(f"Failed to encode batch: {e}")
                    # Return zero vectors for failed batch
                    for idx in batch_indices:
                        embeddings[idx] = np.zeros(self.embedding_dimension, dtype=np.float32)
        
        # Convert to numpy arrays
        result_embeddings = []
        for emb in embeddings:
            if emb is None:
                # Should not happen, but just in case
                emb_array = np.zeros(self.embedding_dimension, dtype=np.float32)
            else:
                emb_array = emb
            result_embeddings.append(emb_array)
        
        if single_input:
            return result_embeddings[0]
        return result_embeddings
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for text."""
        # Use a hash for efficient storage
        import hashlib
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    @staticmethod
    def normalize(vector: NDArray[np.float32]) -> NDArray[np.float32]:
        """
        Normalize a vector to unit length (L2 norm).
        
        Args:
            vector: Input vector
            
        Returns:
            Normalized vector
        """
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm
    
    async def similarity(
        self,
        text1: str,
        text2: str,
        use_cache: bool = True
    ) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            use_cache: Whether to use caching
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        emb1, emb2 = await asyncio.gather(
            self.encode(text1, normalize=True, use_cache=use_cache),
            self.encode(text2, normalize=True, use_cache=use_cache)
        )
        
        return float(np.dot(emb1, emb2))
    
    async def batch_similarity(
        self,
        query_text: str,
        target_texts: List[str],
        use_cache: bool = True
    ) -> List[float]:
        """
        Calculate similarity between a query text and multiple target texts.
        
        Args:
            query_text: Query text
            target_texts: List of target texts
            use_cache: Whether to use caching
            
        Returns:
            List of similarity scores
        """
        # Get embeddings for all texts
        all_texts = [query_text] + target_texts
        embeddings = await self.encode(all_texts, normalize=True, use_cache=use_cache)
        
        query_embedding = embeddings[0]
        target_embeddings = embeddings[1:]
        
        # Calculate similarities
        similarities = []
        for target_emb in target_embeddings:
            similarity = float(np.dot(query_embedding, target_emb))
            similarities.append(similarity)
        
        return similarities
    
    async def find_most_similar(
        self,
        query_text: str,
        target_texts: List[str],
        top_k: int = 5,
        threshold: Optional[float] = None,
        use_cache: bool = True
    ) -> List[Tuple[int, float, str]]:
        """
        Find the most similar texts to a query text.
        
        Args:
            query_text: Query text
            target_texts: List of target texts
            top_k: Number of top results to return
            threshold: Minimum similarity threshold (optional)
            use_cache: Whether to use caching
            
        Returns:
            List of tuples (index, similarity_score, text) sorted by similarity
        """
        similarities = await self.batch_similarity(
            query_text, target_texts, use_cache=use_cache
        )
        
        # Create list of (index, similarity, text) tuples
        results = list(enumerate(zip(similarities, target_texts)))
        results = [(idx, sim, text) for idx, (sim, text) in results]
        
        # Filter by threshold if provided
        if threshold is not None:
            results = [r for r in results if r[1] >= threshold]
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top_k results
        return results[:top_k]
    
    async def semantic_search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        use_cache: bool = True
    ) -> List[Tuple[int, float, str]]:
        """
        Perform semantic search over a collection of documents.
        
        Args:
            query: Search query
            documents: List of documents to search
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            use_cache: Whether to use caching
            
        Returns:
            List of (document_index, similarity_score, document_text) tuples
        """
        return await self.find_most_similar(
            query,
            documents,
            top_k=top_k,
            threshold=similarity_threshold,
            use_cache=use_cache
        )
    
    def calculate_centroid(self, embeddings: List[NDArray[np.float32]]) -> NDArray[np.float32]:
        """
        Calculate the centroid (mean) of multiple embeddings.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Centroid vector
        """
        if not embeddings:
            raise ValueError("Cannot calculate centroid of empty list")
        
        return np.mean(embeddings, axis=0)
    
    async def cluster_similarity(
        self,
        cluster1_texts: List[str],
        cluster2_texts: List[str],
        use_cache: bool = True
    ) -> float:
        """
        Calculate similarity between two clusters of texts using centroid method.
        
        Args:
            cluster1_texts: Texts in first cluster
            cluster2_texts: Texts in second cluster
            use_cache: Whether to use caching
            
        Returns:
            Similarity between cluster centroids
        """
        # Get embeddings for all texts
        all_texts = cluster1_texts + cluster2_texts
        embeddings = await self.encode(all_texts, normalize=True, use_cache=use_cache)
        
        # Split embeddings back into clusters
        n1 = len(cluster1_texts)
        cluster1_embeddings = embeddings[:n1]
        cluster2_embeddings = embeddings[n1:]
        
        # Calculate centroids
        centroid1 = self.calculate_centroid(cluster1_embeddings)
        centroid2 = self.calculate_centroid(cluster2_embeddings)
        
        # Normalize centroids
        centroid1 = self.normalize(centroid1)
        centroid2 = self.normalize(centroid2)
        
        # Calculate similarity
        return float(np.dot(centroid1, centroid2))
    
    async def diversity_score(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> float:
        """
        Calculate diversity score of a set of texts.
        Higher score means more diverse content.
        
        Args:
            texts: List of texts
            use_cache: Whether to use caching
            
        Returns:
            Diversity score (average pairwise distance)
        """
        if len(texts) < 2:
            return 0.0
        
        embeddings = await self.encode(texts, normalize=True, use_cache=use_cache)
        
        # Calculate all pairwise distances
        total_distance = 0.0
        count = 0
        
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                similarity = np.dot(embeddings[i], embeddings[j])
                distance = 1.0 - similarity  # Convert similarity to distance
                total_distance += distance
                count += 1
        
        return total_distance / count if count > 0 else 0.0
    
    async def categorize_text(
        self,
        text: str,
        categories: List[str],
        use_cache: bool = True
    ) -> Tuple[int, float, str]:
        """
        Categorize a text into the most similar category.
        
        Args:
            text: Text to categorize
            categories: List of category descriptions
            use_cache: Whether to use caching
            
        Returns:
            Tuple of (category_index, similarity_score, category_description)
        """
        similarities = await self.batch_similarity(
            text, categories, use_cache=use_cache
        )
        
        # Find the best matching category
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]
        best_category = categories[best_idx]
        
        return (best_idx, best_score, best_category)
    
    async def text_to_embedding_dict(
        self,
        texts: List[str],
        metadata: Optional[List[Dict]] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Convert texts to embedding dictionaries with metadata.
        
        Args:
            texts: List of texts
            metadata: Optional list of metadata dictionaries
            use_cache: Whether to use caching
            
        Returns:
            List of dictionaries with text, embedding, and metadata
        """
        embeddings = await self.encode(texts, normalize=True, use_cache=use_cache)
        
        result = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            item = {
                "text": text,
                "embedding": embedding.tolist(),
                "embedding_dim": self.embedding_dimension
            }
            
            if metadata and i < len(metadata):
                item["metadata"] = metadata[i]
            
            result.append(item)
        
        return result
    
    async def build_embedding_index(
        self,
        items: List[Dict[str, Any]],
        text_field: str = "text",
        id_field: str = "id",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Build an embedding index for fast similarity search.
        
        Args:
            items: List of items with text and metadata
            text_field: Field name containing text
            id_field: Field name containing unique identifier
            use_cache: Whether to use caching
            
        Returns:
            Dictionary containing embedding index
        """
        # Extract texts
        texts = [item[text_field] for item in items]
        
        # Get embeddings
        embeddings = await self.encode(texts, normalize=True, use_cache=use_cache)
        
        # Build index
        index = {
            "model": self.model,
            "dimension": self.embedding_dimension,
            "items": []
        }
        
        for i, (item, embedding) in enumerate(zip(items, embeddings)):
            index_item = {
                "id": item.get(id_field, i),
                "text": item[text_field],
                "embedding": embedding.tolist(),
                "metadata": {k: v for k, v in item.items() 
                           if k not in [text_field, id_field]}
            }
            index["items"].append(index_item)
        
        return index
    
    async def search_index(
        self,
        query: str,
        index: Dict[str, Any],
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search an embedding index.
        
        Args:
            query: Search query
            index: Embedding index built with build_embedding_index
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            use_cache: Whether to use caching
            
        Returns:
            List of search results with similarity scores
        """
        # Get query embedding
        query_embedding = await self.encode(
            query, normalize=True, use_cache=use_cache
        )
        
        # Calculate similarities
        results = []
        for item in index["items"]:
            item_embedding = np.array(item["embedding"], dtype=np.float32)
            similarity = float(np.dot(query_embedding, item_embedding))
            
            if similarity >= similarity_threshold:
                result = {
                    "id": item["id"],
                    "text": item["text"],
                    "similarity": similarity,
                    "metadata": item.get("metadata", {})
                }
                results.append(result)
        
        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return top_k results
        return results[:top_k]
    
    def validate_embedding(self, embedding: NDArray[np.float32]) -> bool:
        """
        Validate that an embedding has the expected properties.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check dimensions
        if embedding.shape != (self.embedding_dimension,):
            logger.warning(f"Embedding has wrong shape: {embedding.shape}")
            return False
        
        # Check for NaN or infinite values
        if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
            logger.warning("Embedding contains NaN or infinite values")
            return False
        
        # Check if all zeros (might indicate encoding failure)
        if np.all(embedding == 0):
            logger.warning("Embedding is all zeros")
            return False
        
        return True
    
    async def encode_with_fallback(
        self,
        texts: Union[str, List[str]],
        fallback_model: str = "text-embedding-ada-002",
        normalize: bool = True,
        use_cache: bool = True
    ) -> Union[NDArray[np.float32], List[NDArray[np.float32]]]:
        """
        Encode text(s) with fallback to another model if primary fails.
        
        Args:
            texts: Single text string or list of texts
            fallback_model: Model to use if primary fails
            normalize: Whether to normalize embeddings
            use_cache: Whether to use caching
            
        Returns:
            Embedding vector(s)
        """
        try:
            return await self.encode(texts, normalize=normalize, use_cache=use_cache)
        except Exception as e:
            logger.warning(f"Primary model failed, falling back to {fallback_model}: {e}")
            
            # Create fallback service
            fallback_service = EmbeddingService(
                model=fallback_model,
                batch_size=self.batch_size,
                cache_size=self.cache_size
            )
            
            return await fallback_service.encode(
                texts, normalize=normalize, use_cache=use_cache
            )
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get embedding service usage statistics.
        
        Returns:
            Dictionary with usage stats
        """
        return {
            "model": self.model,
            "embedding_dimension": self.embedding_dimension,
            "cache_size": len(self._cache),
            "max_cache_size": self.cache_size,
            "batch_size": self.batch_size
        }