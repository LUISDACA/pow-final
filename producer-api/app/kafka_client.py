import json
import os

from confluent_kafka import Producer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

producer = Producer({
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
})


def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}", flush=True)
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]", flush=True)


def send_log(topic: str, data: dict):
    producer.produce(
        topic,
        json.dumps(data).encode("utf-8"),
        callback=delivery_report,
    )
    producer.flush()
