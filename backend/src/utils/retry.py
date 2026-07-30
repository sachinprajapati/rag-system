"""Retry utilities with monitoring integration"""
import time
import functools
from typing import Callable, Any, Optional, Tuple, Type
from src.services.monitoring import get_monitoring_service


def retry_with_monitoring(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    operation_name: str = "operation"
):
    """
    Decorator for retrying operations with exponential backoff and monitoring.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry (exponential backoff)
        exceptions: Tuple of exception types to catch and retry
        operation_name: Name of operation for monitoring logs
        
    Example:
        @retry_with_monitoring(max_attempts=3, operation_name="faiss_search")
        def search_documents(query):
            return faiss_manager.search(query)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            monitoring = get_monitoring_service()
            current_delay = delay
            last_exception = None
            
            # Try to extract user_id and tenant_id from kwargs or args
            user_id = kwargs.get('user_id', 'unknown')
            tenant_id = kwargs.get('tenant_id', 'unknown')
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Attempt the operation
                    result = func(*args, **kwargs)
                    
                    # Log success if there were previous retries
                    if attempt > 1:
                        print(f"✓ {operation_name} succeeded on attempt {attempt}/{max_attempts}")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Log the retry attempt
                    monitoring.log_retry(
                        operation=operation_name,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=str(e),
                        user_id=user_id,
                        tenant_id=tenant_id
                    )
                    
                    if attempt < max_attempts:
                        print(f"⚠ {operation_name} failed (attempt {attempt}/{max_attempts}): {str(e)}")
                        print(f"  Retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"✗ {operation_name} failed after {max_attempts} attempts")
                        
                        # Log final error
                        monitoring.log_error(
                            error_type=type(e).__name__,
                            error_message=f"Failed after {max_attempts} retries: {str(e)}",
                            operation=operation_name,
                            user_id=user_id,
                            tenant_id=tenant_id,
                            retry_count=max_attempts - 1
                        )
                        
                        raise last_exception
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def retry_on_failure(
    func: Callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    operation_name: str = "operation",
    user_id: str = "unknown",
    tenant_id: str = "unknown"
) -> Any:
    """
    Functional retry wrapper (non-decorator version).
    
    Usage:
        result = retry_on_failure(
            lambda: some_operation(),
            max_attempts=3,
            operation_name="my_operation"
        )
    """
    monitoring = get_monitoring_service()
    current_delay = delay
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = func()
            
            if attempt > 1:
                print(f"✓ {operation_name} succeeded on attempt {attempt}/{max_attempts}")
            
            return result
            
        except Exception as e:
            last_exception = e
            
            monitoring.log_retry(
                operation=operation_name,
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(e),
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            if attempt < max_attempts:
                print(f"⚠ {operation_name} failed (attempt {attempt}/{max_attempts}): {str(e)}")
                print(f"  Retrying in {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay *= backoff
            else:
                print(f"✗ {operation_name} failed after {max_attempts} attempts")
                
                monitoring.log_error(
                    error_type=type(e).__name__,
                    error_message=f"Failed after {max_attempts} retries: {str(e)}",
                    operation=operation_name,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    retry_count=max_attempts - 1
                )
                
                raise last_exception
    
    raise last_exception
