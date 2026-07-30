"""Observability and Monitoring Service for RAG System"""
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from src.db.redis_client import RedisClient
from src.core.config import settings


class EventType(str, Enum):
    QUERY = "query"
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    ERROR = "error"
    RETRY = "retry"


class SeverityLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LatencyMetric:
    """Latency tracking for operations"""
    operation: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class QueryLog:
    """Complete query execution log"""
    query_id: str
    timestamp: str
    user_id: str
    tenant_id: str
    query: str
    answer: str
    retrieved_docs_count: int
    search_method: str
    top_k: int
    latency_ms: float
    retrieval_latency_ms: float
    generation_latency_ms: float
    hallucination_score: float
    sources_used: List[str]
    conversation_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ErrorMetric:
    """Error tracking"""
    error_id: str
    timestamp: str
    error_type: str
    error_message: str
    operation: str
    user_id: str
    tenant_id: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    resolved: bool = False


@dataclass
class HallucinationMetric:
    """Hallucination detection metric"""
    query_id: str
    timestamp: str
    query: str
    answer: str
    hallucination_score: float  # 0.0 = grounded, 1.0 = likely hallucinated
    source_overlap_ratio: float  # How much answer overlaps with sources
    has_sources: bool
    sources_count: int
    flagged: bool  # True if score > threshold
    details: Optional[Dict[str, Any]] = None


class MonitoringService:
    """Service for logging, metrics, and observability"""
    
    def __init__(self):
        self.redis = RedisClient(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=2  # Use DB 2 for monitoring
        )
        self.hallucination_threshold = 0.7  # Flag if score > 70%
    
    def generate_id(self, prefix: str = "event") -> str:
        """Generate unique ID for events"""
        timestamp = datetime.utcnow().isoformat()
        return f"{prefix}_{hashlib.md5(timestamp.encode()).hexdigest()[:12]}"
    
    # ========== Latency Tracking ==========
    
    def start_timer(self) -> float:
        """Start timing an operation"""
        return time.time()
    
    def end_timer(self, start_time: float) -> float:
        """End timing and return duration in milliseconds"""
        return (time.time() - start_time) * 1000
    
    def log_latency(
        self,
        operation: str,
        start_time: float,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LatencyMetric:
        """Log latency for an operation"""
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        metric = LatencyMetric(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata
        )
        
        # Store in Redis with 7-day retention
        key = f"monitoring:latency:{operation}:{int(start_time)}"
        self.redis.set(key, json.dumps(asdict(metric)), ex=604800)
        
        # Update rolling average
        self._update_latency_stats(operation, duration_ms)
        
        return metric
    
    def _update_latency_stats(self, operation: str, duration_ms: float):
        """Update rolling latency statistics"""
        stats_key = f"monitoring:stats:latency:{operation}"
        
        try:
            stats_json = self.redis.get(stats_key)
            if stats_json:
                stats = json.loads(stats_json)
            else:
                stats = {
                    "count": 0,
                    "total_ms": 0,
                    "min_ms": float('inf'),
                    "max_ms": 0,
                    "avg_ms": 0
                }
            
            stats["count"] += 1
            stats["total_ms"] += duration_ms
            stats["min_ms"] = min(stats["min_ms"], duration_ms)
            stats["max_ms"] = max(stats["max_ms"], duration_ms)
            stats["avg_ms"] = stats["total_ms"] / stats["count"]
            
            # Keep stats for 30 days
            self.redis.set(stats_key, json.dumps(stats), ex=2592000)
        except Exception as e:
            print(f"Failed to update latency stats: {e}")
    
    # ========== Query & Response Logging ==========
    
    def log_query(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        answer: str,
        retrieved_docs_count: int,
        search_method: str,
        top_k: int,
        latency_ms: float,
        retrieval_latency_ms: float,
        generation_latency_ms: float,
        sources_used: List[str],
        conversation_id: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log complete query execution"""
        query_id = self.generate_id("query")
        
        # Calculate hallucination score
        hallucination_score = self._calculate_hallucination_score(
            answer, sources_used, retrieved_docs_count > 0
        )
        
        query_log = QueryLog(
            query_id=query_id,
            timestamp=datetime.utcnow().isoformat(),
            user_id=user_id,
            tenant_id=tenant_id,
            query=query,
            answer=answer,
            retrieved_docs_count=retrieved_docs_count,
            search_method=search_method,
            top_k=top_k,
            latency_ms=latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=generation_latency_ms,
            hallucination_score=hallucination_score,
            sources_used=sources_used,
            conversation_id=conversation_id,
            error=error,
            metadata=metadata
        )
        
        # Store query log with 30-day retention
        log_key = f"monitoring:query_log:{query_id}"
        self.redis.set(log_key, json.dumps(asdict(query_log)), ex=2592000)
        
        # Add to user's query history for quick access
        user_queries_key = f"monitoring:user_queries:{tenant_id}:{user_id}"
        self.redis.redis.lpush(user_queries_key, query_id)
        self.redis.redis.ltrim(user_queries_key, 0, 999)  # Keep last 1000
        self.redis.redis.expire(user_queries_key, 2592000)
        
        # Update query count
        self._increment_counter("total_queries")
        if error:
            self._increment_counter("failed_queries")
        
        # Log hallucination if detected
        if hallucination_score > self.hallucination_threshold:
            self.log_hallucination(query_id, query, answer, hallucination_score, sources_used)
        
        return query_id
    
    def get_query_log(self, query_id: str) -> Optional[Dict]:
        """Retrieve query log by ID"""
        log_key = f"monitoring:query_log:{query_id}"
        log_json = self.redis.get(log_key)
        return json.loads(log_json) if log_json else None
    
    def get_user_queries(self, user_id: str, tenant_id: str, limit: int = 50) -> List[Dict]:
        """Get recent queries for a user"""
        user_queries_key = f"monitoring:user_queries:{tenant_id}:{user_id}"
        query_ids = self.redis.redis.lrange(user_queries_key, 0, limit - 1)
        
        queries = []
        for query_id in query_ids:
            query_log = self.get_query_log(query_id.decode('utf-8'))
            if query_log:
                queries.append(query_log)
        
        return queries
    
    # ========== Error & Retry Tracking ==========
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        operation: str,
        user_id: str,
        tenant_id: str,
        stack_trace: Optional[str] = None,
        retry_count: int = 0
    ) -> str:
        """Log an error"""
        error_id = self.generate_id("error")
        
        error_metric = ErrorMetric(
            error_id=error_id,
            timestamp=datetime.utcnow().isoformat(),
            error_type=error_type,
            error_message=error_message,
            operation=operation,
            user_id=user_id,
            tenant_id=tenant_id,
            stack_trace=stack_trace,
            retry_count=retry_count,
            resolved=False
        )
        
        # Store error with 30-day retention
        error_key = f"monitoring:error:{error_id}"
        self.redis.set(error_key, json.dumps(asdict(error_metric)), ex=2592000)
        
        # Add to error list for monitoring
        errors_key = f"monitoring:errors:{operation}"
        self.redis.redis.lpush(errors_key, error_id)
        self.redis.redis.ltrim(errors_key, 0, 999)
        self.redis.redis.expire(errors_key, 2592000)
        
        # Update error counters
        self._increment_counter(f"errors:{error_type}")
        self._increment_counter(f"errors:operation:{operation}")
        
        return error_id
    
    def log_retry(
        self,
        operation: str,
        attempt: int,
        max_attempts: int,
        error: str,
        user_id: str,
        tenant_id: str
    ):
        """Log a retry attempt"""
        retry_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "error": error,
            "user_id": user_id,
            "tenant_id": tenant_id
        }
        
        # Store retry log
        retry_key = f"monitoring:retry:{operation}:{int(time.time())}"
        self.redis.set(retry_key, json.dumps(retry_log), ex=604800)
        
        # Update retry counter
        self._increment_counter(f"retries:{operation}")
    
    def get_error_stats(self, operation: Optional[str] = None) -> Dict:
        """Get error statistics"""
        if operation:
            errors_key = f"monitoring:errors:{operation}"
            count = self.redis.redis.llen(errors_key)
            error_ids = self.redis.redis.lrange(errors_key, 0, 9)  # Last 10
        else:
            # Get total errors from counter
            count = self._get_counter_value("total_errors")
            error_ids = []
        
        errors = []
        for error_id in error_ids:
            error_key = f"monitoring:error:{error_id.decode('utf-8')}"
            error_json = self.redis.get(error_key)
            if error_json:
                errors.append(json.loads(error_json))
        
        return {
            "total_errors": count,
            "recent_errors": errors
        }
    
    # ========== Hallucination Monitoring ==========
    
    def _calculate_hallucination_score(
        self,
        answer: str,
        sources: List[str],
        has_retrieved_docs: bool
    ) -> float:
        """
        Calculate hallucination score (0.0 = grounded, 1.0 = likely hallucinated)
        
        Heuristics:
        - No sources = high score
        - Vague/disclaimer answers = low score (honest about limitations)
        - Substantive answer with sources = low score (properly grounded)
        - Generic answer without sources = high score
        """
        # If no documents were retrieved, high hallucination risk
        if not has_retrieved_docs or not sources:
            # Check if answer admits lack of knowledge
            answer_lower = answer.lower()
            honest_phrases = [
                "no documents", "not uploaded", "please upload",
                "i don't have", "i cannot", "not available", "no information"
            ]
            if any(phrase in answer_lower for phrase in honest_phrases):
                return 0.1  # Low risk - honestly stating lack of data
            return 0.9  # High risk - answering without sources
        
        # Documents were retrieved - likely grounded
        answer_lower = answer.lower()
        
        # Check for generic/vague answers (good - not hallucinating)
        honest_phrases = ["i don't have", "i cannot", "not available", "no information", "based on"]
        if any(phrase in answer_lower for phrase in honest_phrases):
            return 0.2  # Low risk if admitting limitations or citing sources
        
        # Check answer length (very short answers are suspicious)
        if len(answer.split()) < 10:
            return 0.6  # Moderate risk for very brief answers
        
        # If we have sources and a substantive answer, assume it's grounded
        # (In production, use semantic similarity or LLM-based fact checking)
        return 0.3  # Low-moderate risk for substantive answers with sources
    
    def log_hallucination(
        self,
        query_id: str,
        query: str,
        answer: str,
        hallucination_score: float,
        sources: List[str]
    ):
        """Log potential hallucination"""
        hallucination_id = self.generate_id("hallucination")
        
        source_overlap_ratio = len([s for s in sources if s.lower() in answer.lower()]) / len(sources) if sources else 0
        
        hallucination_metric = HallucinationMetric(
            query_id=query_id,
            timestamp=datetime.utcnow().isoformat(),
            query=query,
            answer=answer[:500],  # Truncate for storage
            hallucination_score=hallucination_score,
            source_overlap_ratio=source_overlap_ratio,
            has_sources=len(sources) > 0,
            sources_count=len(sources),
            flagged=hallucination_score > self.hallucination_threshold,
            details={"sources": sources}
        )
        
        # Store hallucination metric
        hal_key = f"monitoring:hallucination:{hallucination_id}"
        self.redis.set(hal_key, json.dumps(asdict(hallucination_metric)), ex=2592000)
        
        # Add to flagged list
        flagged_key = "monitoring:hallucinations:flagged"
        self.redis.redis.lpush(flagged_key, hallucination_id)
        self.redis.redis.ltrim(flagged_key, 0, 499)  # Keep last 500
        self.redis.redis.expire(flagged_key, 2592000)
        
        # Update hallucination counter
        self._increment_counter("hallucinations_detected")
    
    def get_hallucination_metrics(self, limit: int = 50) -> List[Dict]:
        """Get recent hallucination detections"""
        flagged_key = "monitoring:hallucinations:flagged"
        hal_ids = self.redis.redis.lrange(flagged_key, 0, limit - 1)
        
        hallucinations = []
        for hal_id in hal_ids:
            hal_key = f"monitoring:hallucination:{hal_id.decode('utf-8')}"
            hal_json = self.redis.get(hal_key)
            if hal_json:
                hallucinations.append(json.loads(hal_json))
        
        return hallucinations
    
    # ========== General Metrics & Counters ==========
    
    def _increment_counter(self, counter_name: str, value: int = 1):
        """Increment a counter"""
        counter_key = f"monitoring:counter:{counter_name}"
        self.redis.redis.incrby(counter_key, value)
        self.redis.redis.expire(counter_key, 2592000)  # 30 days
    
    def _get_counter_value(self, counter_name: str) -> int:
        """Get counter value"""
        counter_key = f"monitoring:counter:{counter_name}"
        value = self.redis.redis.get(counter_key)
        return int(value) if value else 0
    
    def get_system_metrics(self) -> Dict:
        """Get overall system metrics"""
        total_queries = self._get_counter_value("total_queries")
        failed_queries = self._get_counter_value("failed_queries")
        hallucinations = self._get_counter_value("hallucinations_detected")
        
        # Get latency stats for key operations
        query_latency = self._get_latency_stats("query")
        retrieval_latency = self._get_latency_stats("retrieval")
        generation_latency = self._get_latency_stats("generation")
        
        return {
            "total_queries": total_queries,
            "failed_queries": failed_queries,
            "success_rate": (total_queries - failed_queries) / total_queries if total_queries > 0 else 1.0,
            "hallucinations_detected": hallucinations,
            "hallucination_rate": hallucinations / total_queries if total_queries > 0 else 0.0,
            "latency": {
                "query": query_latency,
                "retrieval": retrieval_latency,
                "generation": generation_latency
            }
        }
    
    def _get_latency_stats(self, operation: str) -> Dict:
        """Get latency statistics for an operation"""
        stats_key = f"monitoring:stats:latency:{operation}"
        stats_json = self.redis.get(stats_key)
        
        if stats_json:
            stats = json.loads(stats_json)
            return {
                "avg_ms": round(stats.get("avg_ms", 0), 2),
                "min_ms": round(stats.get("min_ms", 0), 2),
                "max_ms": round(stats.get("max_ms", 0), 2),
                "count": stats.get("count", 0)
            }
        
        return {"avg_ms": 0, "min_ms": 0, "max_ms": 0, "count": 0}


# Singleton instance
_monitoring_service = None


def get_monitoring_service() -> MonitoringService:
    """Get monitoring service singleton"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
