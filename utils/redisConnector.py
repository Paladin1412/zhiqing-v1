# -*- coding: utf-8 -*-
"""
redis database connection
"""
from rediscluster import RedisCluster

# import redis
#
from config.settings import config

#
# redis_conn = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT,
#                          decode_responses=True)

startup_nodes = [{"host": config.REDIS_HOST, "port": config.REDIS_PORT}]

redis_conn = RedisCluster(startup_nodes=startup_nodes, decode_responses=True,
                          password=config.REDIS_PASSWORD)
