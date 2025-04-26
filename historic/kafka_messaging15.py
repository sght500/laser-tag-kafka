from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
import json
import time

KAFKA_MAP_TIMEOUT = 6  # Number of seconds to receive the current map.
KAFKA_LOG_TIMEOUT = 2  # Discard messages which are older than X seconds.

class KafkaMessenger:
    def __init__(self, player_id, bootstrap_servers="localhost:9092", topic="game-events"):
        self.player_id = player_id
        self.topic = topic
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers
        })

        # Send dummy message to warm up
        warmup_message = {
            "type": "warmup",
            "timestamp": time.time()
        }
        self.producer.produce(self.topic, key=self.player_id, value=json.dumps(warmup_message).encode())
        self.producer.poll(0)  # Let the producer process the delivery
        self.producer.flush()  # Force message to be sent immediately


    def _send(self, message_type, payload):
        message = {
            "type": message_type,
            "timestamp": time.time(),
            **payload
        }
        self.producer.produce(
            self.topic,
            key=self.player_id,
            value=json.dumps(message).encode()
        )
        self.producer.poll(0)  # Trigger delivery callbacks. Keep an eye on this. Disable if degrading the game flow.

    def send_wasd_update(self, position, keys):
        payload = {
            "position": position,
            "keys": keys
        }
        self._send("wasd-update", payload)

    def send_bullet_created(self, position, velocity):
        payload = {
            "position": position,
            "velocity": velocity
        }
        self._send("bullet-created", payload)

    def send_hit(self):
        payload = {}
        self._send("got-hit", payload)

    def flush(self):
        self.producer.flush()


class KafkaMessageHandler:
    def __init__(self, player_id, bootstrap_servers="localhost:9092", topic="game-events"):
        self.player_id = player_id
        self.topic = topic

        self.consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": f"player-{player_id}",
            "auto.offset.reset": "latest"
        })

        self.consumer.subscribe([self.topic])
        print(f"🧲 KafkaMessageHandler subscribed to {self.topic}")

    def poll_messages(self, handle_function):
        msg = self.consumer.poll(0.01)
        if msg is None:
            return
        if msg.error():
            if msg.error().code() != KafkaError._PARTITION_EOF:
                print(f"❌ Kafka error: {msg.error()}")
            return

        try:
            key = msg.key().decode() if msg.key() else None
            if key == self.player_id:
                return  # Skip messages from self

            value = json.loads(msg.value().decode())
            seconds_age = time.time() - value.get("timestamp")
            if seconds_age > KAFKA_LOG_TIMEOUT:
                print("Discarding a message which is {:.3f}s old".format(seconds_age))
                return  # Skip old messages

            handle_function(key, value)
        except Exception as e:
            print(f"❌ Error decoding message: {e}")

    def close(self):
        self.consumer.close()


class KafkaMapManager:
    def __init__(self, player_id, bootstrap_servers="localhost:9092", topic=f"game-maze"):
        self.topic = topic
        self.producer = Producer({"bootstrap.servers": bootstrap_servers})
        self.consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": f"group-{player_id}",
            # What to do when there is no initial offset in Kafka or if the current offset does not exist
            # any more on the server (e.g. because that data has been deleted):
            # latest: automatically reset the offset to the latest offset.
            # earliest: automatically reset the offset to the earliest offset
            "auto.offset.reset": "earliest",            
            "enable.auto.commit": False
        })
        self.consumer.subscribe([self.topic])

    def send_map(self, map_data):
        payload = json.dumps(map_data).encode()
        self.producer.produce(self.topic, key="map", value=payload)
        self.producer.poll(0)
        self.producer.flush()

    def send_last_activity(self):
        timestamp = time.time()
        payload = json.dumps(timestamp).encode()
        self.producer.produce(self.topic, key="last-activity", value=payload)
        self.producer.poll(0)

    def read_map_and_activity(self):
        latest_data = {"map": None, "last-activity": None}

        start_time = time.time()
        while True:
            msg = self.consumer.poll(.1)
            if msg is None:
                if time.time() - start_time > KAFKA_MAP_TIMEOUT: break
                else: continue
            if msg.error():
                raise KafkaException(msg.error())

            key = msg.key().decode() if msg.key() else None
            if key in latest_data:
                latest_data[key] = json.loads(msg.value().decode())

        return latest_data["map"], latest_data["last-activity"]

    def close(self):
        self.consumer.close()