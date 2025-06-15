import redis
import json
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """Initialize Redis client."""
        self.host = host
        self.port = port
        self.db = db
        self.client: Optional[redis.Redis] = None
        self.connect()

    def connect(self) -> None:
        """Establish connection to Redis server."""
        try:
            self.client = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            self.client.ping()
            logger.info(f"Successfully connected to Redis at {self.host}:{self.port}")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis at {self.host}:{self.port}: {e}")
            self.client = None # Ensure client is None if connection fails

    def is_connected(self) -> bool:
        """Check if the client is connected to Redis."""
        if self.client:
            try:
                self.client.ping()
                return True
            except redis.exceptions.ConnectionError:
                logger.warning("Redis connection lost. Attempting to reconnect...")
                self.connect() # Attempt to reconnect
                if self.client and self.client.ping(): # Check again after reconnect attempt
                    return True
                logger.error("Failed to reconnect to Redis.")
                return False
        return False

    def set_value(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """Set a value in Redis, optionally with an expiration time.

        Args:
            key (str): The key to set.
            value (Any): The value to set. Will be JSON serialized if it's a dict or list.
            expire_seconds (Optional[int]): Expiration time in seconds.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.is_connected() or self.client is None:
            logger.error("Cannot set value: Redis client not connected.")
            return False
        try:
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)
            
            if expire_seconds:
                self.client.setex(key, expire_seconds, serialized_value)
            else:
                self.client.set(key, serialized_value)
            logger.debug(f"Set value for key '{key}'")
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Error setting value for key '{key}': {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Error serializing value for key '{key}': {e}")
            return False

    def get_value(self, key: str) -> Optional[Any]:
        """Get a value from Redis. Attempts to deserialize JSON strings.

        Args:
            key (str): The key to get.

        Returns:
            Optional[Any]: The value if found and deserialized, otherwise None.
        """
        if not self.is_connected() or self.client is None:
            logger.error("Cannot get value: Redis client not connected.")
            return None
        try:
            value = self.client.get(key)
            if value is None:
                logger.debug(f"Key '{key}' not found in Redis.")
                return None
            try:
                # Attempt to parse as JSON, if it fails, return as string
                deserialized_value = json.loads(value)
                logger.debug(f"Retrieved and deserialized value for key '{key}'")
                return deserialized_value
            except json.JSONDecodeError:
                logger.debug(f"Retrieved value for key '{key}' (not JSON, returned as string)")
                return value # Return as string if not valid JSON
        except redis.exceptions.RedisError as e:
            logger.error(f"Error getting value for key '{key}': {e}")
            return None

    def delete_key(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self.is_connected() or self.client is None:
            logger.error("Cannot delete key: Redis client not connected.")
            return False
        try:
            self.client.delete(key)
            logger.debug(f"Deleted key '{key}'")
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Error deleting key '{key}': {e}")
            return False

    def enqueue_task(self, queue_name: str, task_data: Dict) -> Optional[str]:
        """Enqueue a task (as JSON string) to a Redis list (FIFO queue).

        Args:
            queue_name (str): The name of the queue (Redis list key).
            task_data (Dict): The task data to enqueue.

        Returns:
            Optional[str]: The task_id if successful, None otherwise.
        """
        if not self.is_connected() or self.client is None:
            logger.error(f"Cannot enqueue task: Redis client not connected.")
            return None
        try:
            task_id = task_data.get('task_id') # Assuming task_data contains a 'task_id'
            if not task_id:
                logger.error("Task data must contain a 'task_id'.")
                return None
            serialized_task = json.dumps(task_data)
            self.client.rpush(queue_name, serialized_task)
            logger.info(f"Enqueued task {task_id} to queue '{queue_name}'")
            return task_id
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error enqueuing task to '{queue_name}': {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error serializing task data for queue '{queue_name}': {e}")
            return None

    def dequeue_task(self, queue_name: str, timeout: int = 0) -> Optional[Dict]:
        """Dequeue a task from a Redis list (FIFO queue).
           Uses blocking pop (BLPOP) if timeout > 0.

        Args:
            queue_name (str): The name of the queue.
            timeout (int): Blocking timeout in seconds. 0 for non-blocking.

        Returns:
            Optional[Dict]: The deserialized task data if successful, None otherwise.
        """
        if not self.is_connected() or self.client is None:
            logger.error(f"Cannot dequeue task: Redis client not connected.")
            return None
        try:
            if timeout > 0:
                # BLPOP returns a tuple (list_name, value) or None on timeout
                item = self.client.blpop([queue_name], timeout=timeout)
                serialized_task = item[1] if item else None
            else:
                serialized_task = self.client.lpop(queue_name)

            if serialized_task:
                task_data = json.loads(serialized_task)
                task_id = task_data.get('task_id', 'Unknown')
                logger.info(f"Dequeued task {task_id} from queue '{queue_name}'")
                return task_data
            return None # Queue was empty or timeout occurred
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis error dequeuing task from '{queue_name}': {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error deserializing task data from queue '{queue_name}': {e}")
            return None

# Example Usage (for testing purposes)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    redis_host = 'localhost'
    redis_port = 6379

    # Test connection
    client = RedisClient(host=redis_host, port=redis_port)
    if client.is_connected():
        logger.info("Redis client connected successfully.")

        # Test set and get
        client.set_value("mykey", "hello_redis")
        value = client.get_value("mykey")
        logger.info(f"Got value for 'mykey': {value}")

        client.set_value("myjsonkey", {"name": "test", "value": 123})
        json_value = client.get_value("myjsonkey")
        logger.info(f"Got JSON value for 'myjsonkey': {json_value}")

        # Test enqueue and dequeue
        task_queue = "image_processing_queue"
        sample_task = {"task_id": "task123", "image_data": "some_base64_string", "params": {"scale": 2}}
        
        enqueued_id = client.enqueue_task(task_queue, sample_task)
        if enqueued_id:
            logger.info(f"Task {enqueued_id} enqueued.")

        retrieved_task = client.dequeue_task(task_queue)
        if retrieved_task:
            logger.info(f"Dequeued task: {retrieved_task}")
        else:
            logger.info("No task dequeued (queue might be empty).")
        
        # Test blocking dequeue (will wait for 5 seconds or until a task arrives)
        # To test this, run another script that enqueues a task to 'image_processing_queue'
        # logger.info("Waiting for task with blocking dequeue (5s timeout)...")
        # blocking_task = client.dequeue_task(task_queue, timeout=5)
        # if blocking_task:
        #     logger.info(f"Dequeued blocking task: {blocking_task}")
        # else:
        #     logger.info("Blocking dequeue timed out or queue empty.")

        client.delete_key("mykey")
        client.delete_key("myjsonkey")
    else:
        logger.error("Failed to connect to Redis for testing.")