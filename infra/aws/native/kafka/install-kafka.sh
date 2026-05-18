#!/usr/bin/env bash
set -euo pipefail

KAFKA_VERSION="${KAFKA_VERSION:-4.1.2}"
SCALA_VERSION="${SCALA_VERSION:-2.13}"
KAFKA_PRIVATE_IP="${KAFKA_PRIVATE_IP:-$(hostname -I | awk '{print $1}')}"
KAFKA_LOG_RETENTION_HOURS="${KAFKA_LOG_RETENTION_HOURS:-24}"
KAFKA_TGZ="kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz"
KAFKA_URL="https://www.apache.org/dyn/closer.lua/kafka/${KAFKA_VERSION}/${KAFKA_TGZ}?action=download"
KAFKA_ARCHIVE_URL="https://archive.apache.org/dist/kafka/${KAFKA_VERSION}/${KAFKA_TGZ}"

sudo dnf install -y java-17-amazon-corretto-headless curl tar nftables

cd /tmp
rm -f "$KAFKA_TGZ"

if ! curl -fL --retry 5 --retry-delay 3 "$KAFKA_URL" -o "$KAFKA_TGZ"; then
  echo "Primary Kafka download failed, trying Apache archive..."
  curl -fL --retry 5 --retry-delay 3 "$KAFKA_ARCHIVE_URL" -o "$KAFKA_TGZ"
fi

tar -tzf "$KAFKA_TGZ" >/dev/null
sudo rm -rf /opt/kafka
sudo tar -xzf "$KAFKA_TGZ" -C /opt
sudo mv "/opt/kafka_${SCALA_VERSION}-${KAFKA_VERSION}" /opt/kafka
sudo mkdir -p /var/lib/kafka/data
sudo chown -R ec2-user:ec2-user /opt/kafka /var/lib/kafka

cat > /opt/kafka/config/kraft/server.properties <<EOF
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@${KAFKA_PRIVATE_IP}:9093
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
advertised.listeners=PLAINTEXT://${KAFKA_PRIVATE_IP}:9092
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
log.dirs=/var/lib/kafka/data
num.partitions=3
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
log.retention.hours=${KAFKA_LOG_RETENTION_HOURS}
EOF

if [[ ! -f /var/lib/kafka/data/meta.properties ]]; then
  CLUSTER_ID=$(/opt/kafka/bin/kafka-storage.sh random-uuid)
  /opt/kafka/bin/kafka-storage.sh format -t "$CLUSTER_ID" -c /opt/kafka/config/kraft/server.properties
fi

sudo cp /opt/fraud-log-pipeline/infra/aws/native/kafka/kafka.service /etc/systemd/system/kafka.service
sudo systemctl daemon-reload
sudo systemctl enable --now kafka
sleep 15
KAFKA_PRIVATE_IP="$KAFKA_PRIVATE_IP" /opt/fraud-log-pipeline/infra/aws/native/kafka/create-topics.sh
sudo systemctl status kafka --no-pager
