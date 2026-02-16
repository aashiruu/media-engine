# Media Engine: High-Performance Video Processing on Kubernetes

A scalable, microservices-based video processing platform engineered to handle high-concurrency media workloads. Deployed on **Kubernetes** using **Helm Charts** for reproducible infrastructure.

## Architecture
The system follows a decoupled, event-driven architecture:
* **Media Engine (API):** Python (FastAPI) service handling upload requests and serving status checks.
* **Worker Nodes:** Scalable background workers (Celery) processing video tasks asynchronously.
* **Message Broker:** Redis for high-throughput task queuing.
* **Database:** PostgreSQL for persistent metadata storage.
* **Object Storage:** MinIO (S3-compatible) for handling large video files.
* **Observability:** Prometheus & Grafana for real-time metrics (CPU, Memory, Request Latency).

## Technology Stack
* **Orchestration:** Kubernetes (v1.27)
* **Packaging:** Helm v3
* **Containerization:** Docker
* **Language:** Python 3.10 (FastAPI, Celery)
* **Infrastructure:** Defined as Code (IaC)

## CI/CD Automation
The project implements a **Continuous Integration** pipeline using **GitHub Actions**.
* **Trigger:** Push to `main` branch.
* **Build:** Automatically builds the Docker image.
* **Security:** Authenticates with Docker Hub using encrypted Repository Secrets.
* **Publish:** Pushes the versioned artifact to Docker Hub (`famouswealth/media-engine`).

## Engineering Challenges Solved
* **Resilience:** Implemented "Blue/Green" style database migration to resolve "Zombie" resource conflicts during deployment.
* **Scalability:** Configured Horizontal Pod Autoscalers (HPA) to scale workers based on CPU load.
* **Automation:** Migrated from manual `kubectl` manifests to a modular **Helm Chart** for one-click deployment.

## Quick Start
# 1. Install the Chart
```
helm install media-engine ./media-chart
```

# 2. Verify Deployment
```
kubectl get pods
```

# 3. Access the API
```
kubectl port-forward service/media-engine 8080:80
```
```
curl http://localhost:8080/
```

## Screenshots

<img width="1348" height="545" alt="image" src="https://github.com/user-attachments/assets/deacb2fe-4bc1-4c38-8eed-ff4c05736701" />

<img width="1347" height="378" alt="image" src="https://github.com/user-attachments/assets/f4462602-973c-4b89-b881-d83ecde2c59d" />

<img width="1348" height="337" alt="image" src="https://github.com/user-attachments/assets/4a3dfebf-fd64-4be3-b6d6-b2b83742d4f4" />

<img width="1332" height="628" alt="image" src="https://github.com/user-attachments/assets/a778319e-eca4-4312-b74a-fce0dd10bed3" />
