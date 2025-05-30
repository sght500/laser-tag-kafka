from confluent_kafka import Producer, Consumer, KafkaError
import json
import time

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
            "position": tuple(position),
            "velocity": tuple(velocity)
        }
        self._send("bullet-created", payload)

    def flush(self):
        self.producer.flush()


class KafkaMessageHandler:
    def __init__(self, player_id, bootstrap_servers="localhost:9092", topic="game-events"):
        self.player_id = player_id
        self.topic = topic

        self.consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": f"game-consumer-{player_id}",
            "auto.offset.reset": "earliest"
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
            handle_function(key, value)
        except Exception as e:
            print(f"❌ Error decoding message: {e}")

    def close(self):
        self.consumer.close()