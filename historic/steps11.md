# Setup Process from A to Z

In this setup process we'll start from the begining to the end in the current state of the project.

We already have too many corrections to the setup process, thus a clean setup process from scratch can help.

## Clean up previous docker containers

We have already created some containers and netoworks. Let's clean them up to start fresh.

Stop and remove the kafka container

```bash
sudo docker stop kafka
sudo docker rm kafka
```

Remove the kafka-net network

```bash
sudo docker network rm kafka-net
```



If you haven't created that docker container, don't worry. This is just a clean up step.

## Create a docker container for kafka

We will need the [docker compose](docker-compose.yml) file with the kafka service.

Create the kafka-net network

```bash
sudo docker network create kafka-net
```

Create the [docker compose](docker-compose.yml) file in your home directory

```bash
mkdir ~/kafka
cd ~/kafka
nano docker-compose.yml
```

Copy/paste the content of the file and edit the line:

```
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://192.168.0.9:9092
```

Replace the IP address `192.168.0.9` with the IP address of your linux box at your home network.

### Clean up any previous docker compose

This is a clean up step. Don't worry if it doesn't work.

```bash
sudo docker compose down -v
```

Check for any lingering kafka process

```bash
sudo docker ps -a|grep kf
sudo docker ps -a|grep ka
```

## Continue with docker compose

Let's run the container.

**Remember:** You're in your home directory where your `docker-compose.yml` file is.

```bash
sudo docker compose up -d
```

Check the kafka log and validate kafka is running.

```bash
sudo docker logs kafka
```

Look for a line similar to this one:

```
[2025-04-16 19:06:48,466] INFO [KafkaRaftServer nodeId=1] Kafka Server started (kafka.server.KafkaRaftServer)
```

## Test topic and test messages

Let's create a test topic and send a test message. There's no python interaction at this time.

```bash
sudo docker exec -itunobody kafka bash
kafka-topics.sh --create --topic test-topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

Send a test message

```bash
kafka-console-producer.sh --topic test-topic --bootstrap-server localhost:9092
```

Write something like `Hello there!` and press `<Enter>`. Then press `<Ctrl>-C`

Receive the test message

```bash
kafka-console-consumer.sh --topic test-topic --from-beginning --bootstrap-server localhost:9092
```

Check that your test message shows up and then press `<Ctrl>-C`

Remove the `test-topic`

```bash
kafka-topics.sh --delete --topic test-topic --bootstrap-server localhost:9092
```

## Create the `game-events` topic and test with python

This is the real topic we're going to use in the project. Let's create it and send a test message with python.

Create the `game-events` topic.

```bash
kafka-topics.sh --create --topic game-events \
  --bootstrap-server localhost:9092 \
  --partitions 1 --replication-factor 1 \
  --config retention.ms=1800000 \
  --config cleanup.policy=delete
```

This creates the `game-events` topic with a retention policy of 30 minutes. This is just fine because here we want only real-time messages in this topic and a regular game compltes in less than 10 minutes.

Test the `game-events` topic with python.

In your **Visual Studio Code** in your Windows machine, run the [`producer01.py`](producer01.py). The result should be a line like this one:

```
✅ Message delivered to game-events [0]
```

Still in **Visual Studio Code**, run the [`consumer04.py`](consumer04.py). The result should be a line like this one:

```
📩 Received message: player1 - move-up
```

On both files there's a line with the IP address of my linux box:

```python
SERVER = '192.168.0.9'
```

Be sure to change that IP address with the IP address of your own linux box at your home network.

## List the topics you've created

We created one topics. Let's list it to verify it.

```bash
kafka-topics.sh --list --bootstrap-server localhost:9092
```
