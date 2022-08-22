#/usr/bin/python3
import os
import sys
import redis

REDIS_QUEUE = os.environ.get('REDIS_QUEUE', 'test_operation_logs')
REDIS_CLIENT = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'host.docker.internal'),
    port=os.environ.get('REDIS_PORT', '6379'),
    db=os.environ.get('REDIS_DB', 0))

for line in sys.stdin:
    line = line.strip()
    REDIS_CLIENT.lpush(REDIS_QUEUE, line)
    print(line)
