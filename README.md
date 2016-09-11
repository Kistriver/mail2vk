# Mail2VK

## Requirements
* [Docker](https://www.docker.com/products/overview)
* [Docker Compose](https://docs.docker.com/compose/install/)

## Installing
* Copy config
```bash
cp example.env prod.env
```
* Configure it
* Run mail2vk
```bash
docker-compose up --build
```

## Developing
* Copy config
```bash
cp example.env dev.env
```
* Configure it
* Run tests
```bash
docker-compose -f docker-compose.dev.yml up --build test
```
* Run mail2vk
```bash
docker-compose -f docker-compose.dev.yml up --build service
```
