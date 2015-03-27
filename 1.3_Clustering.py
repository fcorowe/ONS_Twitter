"""
Description:    Run clustering algorithm on all valid tweets in the dataset.
                Attach address info and cluster info to all tweets.
Author:         Bence Komarniczky
Date:           16/March/2015
Python version: 3.4
"""

from datetime import datetime

import ons_twitter.cluster as cl


# start counting time
start_time = datetime.now()
print("Starting clustering: ", start_time, "\n")

# specify databases

mongo_address = [("192.168.0.82:27017", "twitter", "address"),
                 ("192.168.0.87:28000", "twitter", "address"),
                 ("192.168.0.62:28001", "twitter", "address"),
                 ("192.168.0.97:28002", "twitter", "address"),
                 ("192.168.0.97:28003", "twitter", "address")]

twitter_data = (("192.168.0.97:30000", "twitter", "tweets"),
                ("192.168.0.97:30030", "twitter", "tweets"),
                ("192.168.0.97:30031", "twitter", "tweets"),
                ("192.168.0.97:30032", "twitter", "tweets"))

twitter_data = twitter_data[0]
mongo_address = mongo_address[0]

# start clustering
user_no = cl.cluster_all(twitter_data, mongo_address, chunk_range=range(11, 1000),
                         parallel=False, num_cores=1, debug=False)

# give info
print("\n  ****\nFinished clustering at: ", datetime.now(),
      "\n in: ", datetime.now()-start_time,
      "\n Found users:", user_no)