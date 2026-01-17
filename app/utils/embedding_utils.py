# app/services/embedding_utils.py
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from numpy.typing import NDArray
import json
import pickle
from pathlib import Path


class EmbeddingUtils:
    """Utility functions for working with embeddings."""
    
    @staticmethod
    def cosine_similarity(
        vec1: NDArray[np.float32],
        vec2: NDArray[np.float32]
    ) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    @staticmethod
    def euclidean_distance(
        vec1: NDArray[np.float32],
        vec2: NDArray[np.float32]
    ) -> float:
        """
        Calculate Euclidean distance between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Euclidean distance
        """
        return float(np.linalg.norm(vec1 - vec2))
    
    @staticmethod
    def similarity_to_distance(similarity: float) -> float:
        """
        Convert similarity score to distance metric.
        
        Args:
            similarity: Cosine similarity score (-1 to 1)
            
        Returns:
            Distance (0 to 2)
        """
        return 1.0 - similarity
    
    @staticmethod
    def normalize_embeddings(
        embeddings: List[NDArray[np.float32]]
    ) -> List[NDArray[np.float32]]:
        """
        Normalize a list of embeddings to unit length.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            List of normalized embeddings
        """
        normalized = []
        for emb in embeddings:
            norm = np.linalg.norm(emb)
            if norm == 0:
                normalized.append(emb)
            else:
                normalized.append(emb / norm)
        return normalized
    
    @staticmethod
    def average_embeddings(
        embeddings: List[NDArray[np.float32]],
        weights: Optional[List[float]] = None
    ) -> NDArray[np.float32]:
        """
        Calculate weighted average of embeddings.
        
        Args:
            embeddings: List of embedding vectors
            weights: Optional list of weights
            
        Returns:
            Weighted average embedding
        """
        if not embeddings:
            raise ValueError("Cannot average empty list of embeddings")
        
        if weights is None:
            weights = [1.0] * len(embeddings)
        
        if len(weights) != len(embeddings):
            raise ValueError("Weights must have same length as embeddings")
        
        # Convert to numpy arrays for efficient computation
        emb_array = np.array(embeddings)
        weights_array = np.array(weights).reshape(-1, 1)
        
        # Calculate weighted average
        weighted_sum = np.sum(emb_array * weights_array, axis=0)
        total_weight = np.sum(weights)
        
        return (weighted_sum / total_weight).astype(np.float32)
    
    @staticmethod
    def find_nearest_neighbors(
        query_embedding: NDArray[np.float32],
        candidate_embeddings: List[NDArray[np.float32]],
        top_k: int = 5,
        distance_metric: str = "cosine"
    ) -> List[Tuple[int, float]]:
        """
        Find nearest neighbors using specified distance metric.
        
        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embeddings
            top_k: Number of neighbors to return
            distance_metric: 'cosine' or 'euclidean'
            
        Returns:
            List of (index, distance/similarity) tuples
        """
        if distance_metric == "cosine":
            # For cosine, we want highest similarity (not smallest distance)
            similarities = [
                EmbeddingUtils.cosine_similarity(query_embedding, cand)
                for cand in candidate_embeddings
            ]
            # Get indices of top_k highest similarities
            indices = np.argsort(similarities)[-top_k:][::-1]
            results = [(idx, similarities[idx]) for idx in indices]
        elif distance_metric == "euclidean":
            distances = [
                EmbeddingUtils.euclidean_distance(query_embedding, cand)
                for cand in candidate_embeddings
            ]
            # Get indices of top_k smallest distances
            indices = np.argsort(distances)[:top_k]
            results = [(idx, distances[idx]) for idx in indices]
        else:
            raise ValueError(f"Unsupported distance metric: {distance_metric}")
        
        return results
    
    @staticmethod
    def cluster_embeddings_kmeans(
        embeddings: List[NDArray[np.float32]],
        n_clusters: int,
        max_iter: int = 100
    ) -> Tuple[List[int], List[NDArray[np.float32]]]:
        """
        Simple k-means clustering for embeddings.
        
        Args:
            embeddings: List of embedding vectors
            n_clusters: Number of clusters
            max_iter: Maximum iterations
            
        Returns:
            Tuple of (cluster_labels, cluster_centers)
        """
        from sklearn.cluster import KMeans
        
        # Convert to numpy array
        X = np.array(embeddings)
        
        # Perform k-means clustering
        kmeans = KMeans(
            n_clusters=min(n_clusters, len(embeddings)),
            max_iter=max_iter,
            random_state=42,
            n_init=10
        )
        labels = kmeans.fit_predict(X)
        centers = kmeans.cluster_centers_
        
        return labels.tolist(), [c.astype(np.float32) for c in centers]
    
    @staticmethod
    def save_embeddings(
        embeddings: Dict[str, Any],
        filepath: str,
        format: str = "json"
    ) -> None:
        """
        Save embeddings to file.
        
        Args:
            embeddings: Dictionary containing embeddings
            filepath: Path to save file
            format: 'json' or 'pickle'
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            # Convert numpy arrays to lists for JSON serialization
            embeddings_serializable = EmbeddingUtils._prepare_for_json(embeddings)
            with open(filepath, 'w') as f:
                json.dump(embeddings_serializable, f, indent=2)
        elif format == "pickle":
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def load_embeddings(
        filepath: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Load embeddings from file.
        
        Args:
            filepath: Path to file
            format: 'json' or 'pickle'
            
        Returns:
            Dictionary containing embeddings
        """
        if format == "json":
            with open(filepath, 'r') as f:
                data = json.load(f)
            # Convert lists back to numpy arrays if needed
            return EmbeddingUtils._restore_from_json(data)
        elif format == "pickle":
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def _prepare_for_json(data: Any) -> Any:
        """Prepare data for JSON serialization."""
        if isinstance(data, dict):
            return {k: EmbeddingUtils._prepare_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [EmbeddingUtils._prepare_for_json(item) for item in data]
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, np.floating):
            return float(data)
        elif isinstance(data, np.integer):
            return int(data)
        else:
            return data
    
    @staticmethod
    def _restore_from_json(data: Any) -> Any:
        """Restore data from JSON format."""
        if isinstance(data, dict):
            return {k: EmbeddingUtils._restore_from_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Check if this looks like an embedding vector
            if (len(data) > 0 and 
                isinstance(data[0], (int, float)) and
                len(data) in [1536, 3072, 768]):  # Common embedding dimensions
                return np.array(data, dtype=np.float32)
            return [EmbeddingUtils._restore_from_json(item) for item in data]
        else:
            return data
    
    @staticmethod
    def create_embedding_matrix(
        texts: List[str],
        embeddings: List[NDArray[np.float32]]
    ) -> Dict[str, Any]:
        """
        Create an embedding matrix for efficient similarity calculations.
        
        Args:
            texts: List of texts
            embeddings: Corresponding embeddings
            
        Returns:
            Dictionary containing embedding matrix
        """
        if len(texts) != len(embeddings):
            raise ValueError("Texts and embeddings must have same length")
        
        # Create matrix (n_samples x n_features)
        matrix = np.array(embeddings, dtype=np.float32)
        
        return {
            "texts": texts,
            "matrix": matrix,
            "n_samples": len(texts),
            "n_features": matrix.shape[1]
        }
    
    @staticmethod
    def batch_cosine_similarity(
        query_embedding: NDArray[np.float32],
        embedding_matrix: NDArray[np.float32]
    ) -> NDArray[np.float32]:
        """
        Calculate cosine similarity between query and all embeddings in matrix.
        
        Args:
            query_embedding: Query embedding vector
            embedding_matrix: Matrix of embeddings
            
        Returns:
            Array of similarity scores
        """
        # Normalize query and matrix
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        matrix_norms = np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
        matrix_normalized = embedding_matrix / matrix_norms
        
        # Calculate similarities
        similarities = np.dot(matrix_normalized, query_norm)
        return similarities.astype(np.float32)