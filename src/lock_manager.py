import os
import threading
from contextlib import contextmanager
from typing import Optional
from loguru import logger
import redis
from redis.lock import Lock as RedisLock


class LockManager:
    """
    Unified lock manager supporting both in-memory and Redis-based distributed locking.
    
    Environment Variables:
    - LOCK_PROVIDER: "memory" or "redis" (default: memory)
    - REDIS_HOST: Redis host (default: localhost)
    - REDIS_PORT: Redis port (default: 6379)
    - REDIS_DB: Redis database number (default: 0)
    - REDIS_PASSWORD: Redis password (optional)
    - LOCK_TIMEOUT: Lock timeout in seconds (default: 30)
    """
    
    def __init__(self):
        self.provider = os.getenv("LOCK_PROVIDER", "memory").lower()
        self.lock_timeout = int(os.getenv("LOCK_TIMEOUT", "30"))
        
        # In-memory locks dictionary
        self._memory_locks = {}
        self._memory_locks_lock = threading.Lock()
        
        # Redis client
        self._redis_client: Optional[redis.Redis] = None
        
        if self.provider == "redis":
            self._init_redis()
        
        logger.info(f"LockManager initialized with provider: {self.provider}")
    
    def _init_redis(self):
        """Initialize Redis client."""
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            redis_password = os.getenv("REDIS_PASSWORD")
            
            self._redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password if redis_password else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            self._redis_client.ping()
            logger.info(f"Redis connection established: {redis_host}:{redis_port}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            logger.warning("Falling back to in-memory locking")
            self.provider = "memory"
            self._redis_client = None
    
    def _get_memory_lock(self, key: str) -> threading.Lock:
        """Get or create an in-memory lock for the given key."""
        with self._memory_locks_lock:
            if key not in self._memory_locks:
                self._memory_locks[key] = threading.Lock()
            return self._memory_locks[key]
    
    @contextmanager
    def acquire_lock(self, key: str, blocking: bool = True, timeout: Optional[int] = None):
        """
        Acquire a lock for the given key.
        
        Args:
            key: Lock identifier
            blocking: Whether to block waiting for lock (default: True)
            timeout: Lock timeout in seconds (default: uses LOCK_TIMEOUT env var)
        
        Yields:
            bool: True if lock was acquired
        
        Example:
            with lock_manager.acquire_lock("my_resource"):
                # Critical section
                pass
        """
        if timeout is None:
            timeout = self.lock_timeout
        
        lock_acquired = False
        lock = None
        
        try:
            if self.provider == "redis" and self._redis_client:
                # Redis distributed lock
                lock = RedisLock(
                    self._redis_client,
                    name=f"lock:{key}",
                    timeout=timeout,
                    blocking_timeout=timeout if blocking else 0.1,
                )
                lock_acquired = lock.acquire(blocking=blocking, blocking_timeout=timeout if blocking else 0.1)
                
                if lock_acquired:
                    logger.debug(f"Acquired Redis lock: {key}")
                else:
                    logger.warning(f"Failed to acquire Redis lock: {key}")
                
            else:
                # In-memory lock
                lock = self._get_memory_lock(key)
                lock_acquired = lock.acquire(blocking=blocking, timeout=timeout if blocking else None)
                
                if lock_acquired:
                    logger.debug(f"Acquired in-memory lock: {key}")
                else:
                    logger.warning(f"Failed to acquire in-memory lock: {key}")
            
            yield lock_acquired
            
        except Exception as e:
            logger.error(f"Error acquiring lock {key}: {e}")
            yield False
            
        finally:
            if lock_acquired and lock:
                try:
                    if self.provider == "redis" and isinstance(lock, RedisLock):
                        lock.release()
                        logger.debug(f"Released Redis lock: {key}")
                    elif isinstance(lock, threading.Lock):
                        lock.release()
                        logger.debug(f"Released in-memory lock: {key}")
                except Exception as e:
                    logger.error(f"Error releasing lock {key}: {e}")


# Injector module for LockManager
from injector import Module, provider, singleton as injector_singleton


class LockModule(Module):
    """Dependency injection module for LockManager."""
    
    @provider
    @injector_singleton
    def provide_lock_manager(self) -> LockManager:
        """Provide a singleton LockManager instance."""
        return LockManager()
