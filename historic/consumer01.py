# consumer.py
from confluent_kafka import Consumer

conf = {
    'bootstrap.servers': '192.168.0.9:9092',
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

        print(f"📩 Received message: {msg.key().decode()} - {msg.value().decode()}")
except KeyboardInterrupt:
    pass
finally:
    consumer.close()
