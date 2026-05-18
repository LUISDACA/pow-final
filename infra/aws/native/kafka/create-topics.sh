#!/usr/bin/env bash
set -euo pipefail

KAFKA_PRIVATE_IP="${KAFKA_PRIVATE_IP:-$(hostname -I | awk '{print $1}')}"

/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${KAFKA_PRIVATE_IP}:9092" --create --if-not-exists --topic logs.auth --partitions 3 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${KAFKA_PRIVATE_IP}:9092" --create --if-not-exists --topic logs.api --partitions 3 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${KAFKA_PRIVATE_IP}:9092" --create --if-not-exists --topic logs.sql_injection --partitions 3 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${KAFKA_PRIVATE_IP}:9092" --create --if-not-exists --topic fraud.alerts --partitions 3 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${KAFKA_PRIVATE_IP}:9092" --list
