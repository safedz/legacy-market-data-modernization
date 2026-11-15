
# Docker

`Dockerfile.pipeline` packages the pipeline using Python 3.12.

## Build the Pipeline

Build the Docker image from the project root:

```bash
docker build -f deployment/docker/Dockerfile.pipeline -t pearl-pipeline .
```

Run the pipeline container:

```bash
docker run --rm -v "${PWD}/data:/app/data" pearl-pipeline
```

## Run the Whole Stack

To start PostgreSQL, the pipeline, loader, and database checks together:

```bash
docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.data.yml up --build
```

## Important Note

The Compose files retain the development password from `docker-compose.yml`. Change this password before using the configuration in any shared deployment.
