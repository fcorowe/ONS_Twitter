"""
Description:
Author: Bence Komarniczky
Date:
Python version: 3.4
"""

from datetime import datetime
import ons_twitter.cluster as cl

start_time = datetime.now()

test_tweets = ["127.0.0.1:27017", "test", "tweets"]
mongo_address = ["192.168.0.82:27017", "twitter", "address"]

a = cl.cluster_one_chunk(test_tweets, mongo_address, 31)
print(a)


print(datetime.now() - start_time)