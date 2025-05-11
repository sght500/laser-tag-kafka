# Kafka Setup on Windows (No Admin Rights, Java 1.8)

This guide explains how to install and run Kafka 3.9.0 on a Windows machine **without admin rights**. It assumes Java 1.8 is already installed and available on the system `PATH`.

> ⚠️ Kafka 4.x requires Java 11+. Kafka 3.9.0 works with Java 1.8 and is the recommended version for this setup.

---

## PART I - Download, Setup, and Start Kafka

### 1. **Download Kafka 3.9.0**

Go to the [Kafka download page](https://kafka.apache.org/downloads) and get:

- Version: **3.9.0**
- Scala: **2.13**
- File: kafka_2.13-3.9.0.tgz

### 2. **Extract the contents**  
   Extract the `.tgz` file using a compatible extractor (7-Zip or similar) and place everything into:

```
C:\kfk
```

> ⚠️ Use a short path like `C:\kfk` to avoid long path issues in Windows.

### 3. **Create the required folders**

```
C:\kfk\zookeeper
C:\kfk\kafka-logs
```

### 4. **Edit `zookeeper.properties`**

File: `C:\kfk\config\zookeeper.properties`  
Modify this line:

```properties
dataDir=C://kfk//zookeeper
```

### 5. **Edit `server.properties`**

First, check the IP address of the Windows PC in which you will run Kafka. You can run this command:

```cmd
ipconfig
```

And look for a line like this one:

```
IPv4 Address. . . . . . . . . . . : 192.168.1.29
```

Now, edit this file: `C:\kfk\config\server.properties` and modify thes lines:

```properties
log.dirs=C://kfk//kafka-logs
```

and

```properties
advertised.listeners=PLAINTEXT://192.168.1.29:9092
```

Use the IP address of your Windows PC in which you will run Kafka.

### 6. **Start ZooKeeper**

Open **Windows Terminal** or **Command Prompt** and run:

```cmd
cd C:\kfk
.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties
```

### 7. **Start Kafka**

In another terminal tab or window:

```cmd
cd C:\kfk
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

## PART II - Test Kafka with CLI Commands

Use new tabs for each of the following steps:

### 1. **Create a test topic**

```cmd
cd C:\kfk
.\bin\windows\kafka-topics.bat --create --topic test-topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

### 2. **Send a test message**

```cmd
.\bin\windows\kafka-console-producer.bat --topic test-topic --bootstrap-server localhost:9092
```

Type:

```
Hello There!
```

Then press `<Enter>` and `<Ctrl+C>` to exit.

### 3. Receive the test message

```cmd
.\bin\windows\kafka-console-consumer.bat --topic test-topic --from-beginning --bootstrap-server localhost:9092
```

You should see:

```
Hello There!
```

Press `<Ctrl+C>` to exit.

### 4. Topic Deletion Note (Optional)
Kafka on Windows doesn't always support topic deletion reliably due to file lock issues and other quirks. For this reason, we skip deleting the test topic here.

---

## PART III - Set Up the `game-events` Topic and Test with Python

This is the real topic we're going to use in the project. Let's create it and send a test message with python.

### 1. Create the `game-events` topic

```cmd
.\bin\windows\kafka-topics.bat --create --topic game-events --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 --config retention.ms=600000 --config cleanup.policy=delete
```

### 2. Edit the `producer.py` and `consumer.py` scripts.

Edit the `producer.py` and `consumer.py` scripts to use the IP address of your Kafka PC.

Edit the following line on both files:

```python
SERVER = '192.168.1.29'
```

Use the IP address of your Windows PC in which you are runing Kafka.

### 3. Send a test message with Python

```cmd
cd <path-to>\laser-tag-kafka\setup\
py .\producer.py
```

The result should be a line like this one:

```
✅ Message delivered to game-events [0]
```

### 4. Receive a test message with Python

```cmd
py .\consumer.py
```

The result should be a line like this one:

```
📩 Received message: player1 - move-up
```

---

## ✅ Success

You now have Kafka running locally on a Windows machine with no admin rights, using Java 1.8. You're ready to run and test the **Laser Tag Kafka** game.
