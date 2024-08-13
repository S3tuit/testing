import json
import logging
import os

from dotenv import load_dotenv
from kafka import TopicPartition, OffsetAndMetadata
from kafka.consumer import KafkaConsumer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

load_dotenv(verbose=True)


def people_key_deserializer(key):
    return key.decode('utf-8')

def people_value_deserializer(value):
    return json.loads(value.decode('utf-8'))


def main():
    logger.info(f"""
                Started Python Consumer
                fro topic {os.environ['TOPICS_PEOPLE_BASIC_NAME']}
                """)
    
    consumer = KafkaConsumer(bootstrap_servers = os.environ['BOOTSTRAP_SERVERS'],
                             group_id=os.environ['CONSUMER_GROUP'],
                             key_deserializer=people_key_deserializer,
                             value_deserializer=people_value_deserializer,
                             enable_auto_commit=False)
    
    consumer.subscribe([os.environ['TOPICS_PEOPLE_BASIC_NAME']])
    for record in consumer:
        logger.info(f"""
                    __________________
                    Consumed a message:
                    {record}
                    ___________________
                    """)
        
        topic_partition = TopicPartition(record.topic, record.partition)
        offset = OffsetAndMetadata(record.offset + 1, record.timestamp)
        consumer.commit({
            topic_partition: offset
        })

if __name__ == '__main__':
    main()