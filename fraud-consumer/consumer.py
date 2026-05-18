import json
import os
import time

from confluent_kafka import Consumer, KafkaException

from database import save_access_log, save_fraud_alert, wait_for_database
from rules import analyze_log

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

TOPICS = [
    "logs.auth",
    "logs.api",
    "logs.sql_injection",
]


def create_consumer():
    return Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "fraud-detector-group",
        "auto.offset.reset": "earliest",
    })


def main():
    wait_for_database()

    consumer = create_consumer()
    consumer.subscribe(TOPICS)

    print("Fraud consumer started...", flush=True)

    try:
        while True:
            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                print(f"Consumer error: {message.error()}", flush=True)
                continue

            try:
                log = json.loads(message.value().decode("utf-8"))
                print(f"Received log: {log}", flush=True)

                save_access_log(log)
                alerts = analyze_log(log)

                for alert in alerts:
                    print(f"ALERT DETECTED: {alert}", flush=True)
                    save_fraud_alert(log, alert)

            except Exception as error:
                print(f"Error processing message: {error}", flush=True)

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Fraud consumer stopped.", flush=True)
    except KafkaException as error:
        print(f"Kafka error: {error}", flush=True)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
