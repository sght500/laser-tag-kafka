# consumer.py
from confluent_kafka import Consumer

SERVER = '192.168.0.9'

conf = {
    'bootstrap.servers': f'{SERVER}:9092',
    'group.id': 'game-consumers',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)
consumer.subscribe(['game-events'])

print("🔄 Waiting for messages...")
try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"❌ Consumer error: {msg.error()}")
            continue

        key = msg.key().decode() if msg.key() else "🔑 None"
        value = msg.value().decode() if msg.value() else "❓ No value"
        print(f"📩 Received message: {key} - {value}")
except KeyboardInterrupt:
    pass
finally:
    consumer.close()
