from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
import json
import time

KAFKA_LOG_TIMEOUT = 2  # Discard messages which are older than X seconds.
KAFKA_OWN_MESSAGES = 5  # Number of messages to calate LAN Round Trip Time.
KAFKA_MIN_MESSAGES = 10  # Number of messages to calculate estimated_offset.


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

    def send_waiting_2_join(self, map):
        payload = {
            "map": map
        }
        self._send("waiting-2-join", payload)

    def send_spawn(self, position):
        payload = {
            "position": position
        }
        self._send("player-spawn", payload)

    def send_wasd_update(self, position, keys, map):
        payload = {
            "position": position,
            "keys": keys,
            "map": map
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

    def send_player_exit(self):
        payload = {}  # We may extend this later, adding a reason. (eg. player-died, disconnected, etc.)
        self._send("player-exit", payload)

    def flush(self):
        self.producer.flush()


class KafkaMessageHandler:
    def __init__(self, player_id, bootstrap_servers="localhost:9092", topic="game-events"):
        self.player_id = player_id
        self.topic = topic
        self.estimated_rtt = None  # LAN Round Trip Time
        self.self_ages = [] # List of 5 self message ages.
        self.estimated_offset = {}  # One per remote_id
        self.message_ages = {}  # Key=remote_id. Value=List of 10 message ages.

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
            value = json.loads(msg.value().decode())
            message_age = time.time() - value.get("timestamp")
            if key == self.player_id:
                if len(self.self_ages) < KAFKA_OWN_MESSAGES:
                    self.self_ages.append(message_age)
                    if len(self.self_ages) == KAFKA_OWN_MESSAGES:
                        self.estimated_rtt = sum(self.self_ages) / KAFKA_OWN_MESSAGES
                        print(f"[{key}] Estimated Round Trip: {self.estimated_rtt:.3f}s")
                return  # Skip messages from self

            if key in self.message_ages:
                if key not in self.estimated_offset or len(self.message_ages[key]) < KAFKA_MIN_MESSAGES:
                    # Continue collecting message ages while there's no offset or while there are too few of them.
                    self.message_ages[key].append(message_age)
                if key not in self.estimated_offset and len(self.message_ages[key]) >= KAFKA_MIN_MESSAGES and \
                self.estimated_rtt != None:
                    # Once we have enough samples, compute estimated offset if your have an estimated RTT.
                    avg_age = sum(self.message_ages[key]) / len(self.message_ages[key])
                    self.estimated_offset[key] = avg_age - self.estimated_rtt
                    print(f"[{key}] Estimated offset: {self.estimated_offset[key]:.3f}s")
                if key in self.estimated_offset:
                    # Already have offset: check if message is too old
                    seconds_age = message_age - self.estimated_offset[key]
                    if seconds_age > KAFKA_LOG_TIMEOUT:
                        print("Discarding a message which is {:.3f}s old from [{}]".format(seconds_age, key))
                        return  # Skip old messages
            else:
                # First time seeing this key — initialize tracking
                self.message_ages[key] = [message_age]
                  
            # Finally, handle the message
            handle_function(key, value)

        except Exception as e:
            print(f"❌ Error decoding message: {e}")
            print(msg.key(), msg.value())

    def close(self):
        self.consumer.close()