# -*- coding: utf-8 -*-
"""
redis database connection
"""
import redis

from config.settings import config

redis_conn = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT,
                         decode_responses=True)

# from rediscluster import RedisCluster
#
# startup_nodes = [{"host": "web02cn.haetek.com", "port": "7001"}]
#
# redis_conn = RedisCluster(startup_nodes=startup_nodes, decode_responses=True,
#                   password='!password123')
