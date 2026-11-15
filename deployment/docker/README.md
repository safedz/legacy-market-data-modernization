
Docker
`Dockerfile.pipeline` packages the pipeline (Python 3.12). Build from the project root:
    docker build -f deployment/docker/Dockerfile.pipeline -t pearl-pipeline .
    docker run --rm -v "${PWD}/data:/app/data" pearl-pipeline

Whole stack (PostgreSQL + pipeline + loader + database checks):
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.data.yml up --build

The compose files keep the development password from `docker-compose.yml`. Change it before any shared deployment.