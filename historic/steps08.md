# Setup Process from A to Z

In this setup process we'll start from the begining to the end in the current state of the project.

We already have too many corrections to the setup process, thus a clean setup process from scratch can help.

## Clean up previous docker containers and networks

We have already created some containers and netoworks. Let's clean them up to start fresh.

Remove the kafka container

```bash
sudo docker rm kafka
```

Remove the kafka-net network

```bash
sudo docker network rm kafka-net
```

If you haven't created those docker items, don't worry. This is just a clean up step.

## Docker for Windows?

As you can see, I previously ran docker in my Linux box at home. 

Let's try docker for windows so that we can test this project without the need to be at home to run docker.

[Install DockerRun for Windows](https://apps.microsoft.com/detail/9NVBZPBTK78W)

Nop! It didn't work.