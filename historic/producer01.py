# producer.py
from confluent_kafka import Producer

SERVER = '192.168.0.9'

conf = {
    'bootstrap.servers': f'{SERVER}:9092'
}

producer = Producer(conf)

def delivery_report(err, msg):
    if err is not None:
        print(f"❌ Message delivery failed: {err}")
    else:
        print(f"✅ Message delivered to {msg.topic()} [{msg.partition()}]")

# Send a message
producer.produce('game-events', key='player1', value='move-up', callback=delivery_report)

# Wait for all messages to be delivered
producer.flush()
