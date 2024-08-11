import uuid
import os
from typing import List
import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from faker import Faker

from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError
from kafka.producer import KafkaProducer

from commands import CreatePeopleCommand
from entities import Person



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

load_dotenv(verbose=True)

app = FastAPI()

@app.on_event('startup')
async def startup_event():
    client = KafkaAdminClient(bootstrap_servers=os.environ['BOOTSTRAP_SERVERS'])
    topic = NewTopic(
        name=os.environ['TOPICS_PEOPLE_BASIC_NAME'],
        num_partitions=int(os.environ['TOPICS_PEOPLE_BASIC_PARTITIONS']),
        replication_factor=int(os.environ['TOPICS_PEOPLE_BASIC_REPLICAS'])
    )
    
    try:
        client.create_topics([topic])
    except TopicAlreadyExistsError as e:
        print("Topic already exists.")
    finally:
        client.close()

def make_producer():
    producer = KafkaProducer(bootstrap_servers=os.environ['BOOTSTRAP_SERVERS'],
                             linger_ms=int(os.environ['TOPICS_PEOPLE_LINGER_MS']),
                             retries=int(os.environ['TOPICS_PEOPLE_RETRIES']),
                             max_in_flight_requests_per_connection=int(os.environ['TOPICS_PEOPLE_INFLIGHT_REQS']),
                             acks=os.environ['TOPICS_PEOPLE_ACK'])
    return producer


class SuccessHandler:
    def __init__(self, person):
        self.person = person
        
    def __call__(self, rec_metadata):
        logger.info(f"""
                    Successfully produced
                    person {self.person}
                    to topic {rec_metadata.topic}
                    and partition {rec_metadata.partition}
                    at offset {rec_metadata.offset}""")


class ErrorHandler:
    def __init__(self, person):
        self.person = person
        
    def __call__(self, ex):
        logger.error(f"Failed producing person {self.person}", exc_info=ex)



@app.post('/api/people', status_code=201, response_model=List[Person])
async def create_people(cmd: CreatePeopleCommand):
    people: List[Person] = []
    
    faker = Faker()
    producer = make_producer()
    
    for _ in range(cmd.count):
        person = Person(id=str(uuid.uuid4()), name=faker.name(), title=faker.job().title())
        people.append(person)
        producer.send(topic=os.environ['TOPICS_PEOPLE_BASIC_NAME'],
                      key=person.title.lower().replace(r's+', '-').encode('utf-8'),
                      value=person.json().encode('utf-8'))\
                .add_callback(SuccessHandler(person))\
                .add_errback(ErrorHandler(person))
                        
        
    producer.flush()
    
    return people