# TORE Matrix Labs V3 - Production Deployment Guide

## Overview

This guide covers deploying the TORE Matrix V3 Document Ingestion System in production environments. The system provides enterprise-grade document processing with high availability, scalability, and monitoring.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Load Balancer │────▶│   API Servers   │────▶│  Redis Cluster  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Queue Workers  │────▶│  Unstructured   │
                        └─────────────────┘     │   API Service   │
                               │                └─────────────────┘
                               ▼
                        ┌─────────────────┐
                        │  Object Storage │
                        │   (S3/MinIO)    │
                        └─────────────────┘
```

## Prerequisites

### Infrastructure Requirements

- **Kubernetes 1.24+** or Docker Swarm
- **Helm 3.10+** (for Kubernetes deployment)
- **Redis 7.0+** (clustered for HA)
- **PostgreSQL 15+** (with replication)
- **S3-compatible object storage** (AWS S3, MinIO, etc.)
- **Unstructured.io API** (hosted or cloud)

### Resource Requirements

#### Minimum (Development/Testing)
- **CPU**: 4 cores
- **Memory**: 8GB RAM
- **Storage**: 100GB SSD
- **Network**: 1Gbps

#### Production (High Availability)
- **API Servers**: 3+ instances, 2 CPU cores, 4GB RAM each
- **Queue Workers**: 5+ instances, 4 CPU cores, 8GB RAM each
- **Redis Cluster**: 3+ nodes, 2 CPU cores, 4GB RAM each
- **PostgreSQL**: Master + 2 replicas, 4 CPU cores, 8GB RAM each
- **Load Balancer**: 2+ instances, 2 CPU cores, 2GB RAM each
- **Storage**: 1TB+ SSD for documents, separate volumes for databases

### Software Requirements

- **Docker 20.10+**
- **Python 3.11+** (if running natively)
- **Node.js 18+** (for frontend, if applicable)

## Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```bash
# Environment
TOREMATRIX_ENV=production
TOREMATRIX_LOG_LEVEL=INFO
TOREMATRIX_DEBUG=false

# Database Configuration
DATABASE_URL=postgresql://torematrix:${DB_PASSWORD}@postgres-cluster:5432/torematrix
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# Redis Configuration  
REDIS_URL=redis://redis-cluster:6379/0
REDIS_MAX_CONNECTIONS=100
REDIS_SOCKET_TIMEOUT=30
REDIS_CONNECTION_POOL_SIZE=50

# Unstructured.io Configuration
UNSTRUCTURED_API_URL=https://api.unstructured.io
UNSTRUCTURED_API_KEY=${UNSTRUCTURED_API_KEY}
UNSTRUCTURED_MAX_CONCURRENT=10
UNSTRUCTURED_TIMEOUT=300
UNSTRUCTURED_RETRY_ATTEMPTS=3

# Object Storage Configuration
STORAGE_BACKEND=s3
S3_BUCKET=torematrix-documents-prod
S3_REGION=us-east-1
S3_ENDPOINT=https://s3.amazonaws.com
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

# Queue Configuration
QUEUE_MAX_WORKERS=10
QUEUE_JOB_TIMEOUT=3600
QUEUE_MAX_RETRIES=3
QUEUE_BATCH_SIZE=5
QUEUE_PRIORITY_ENABLED=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RATE_LIMIT=100
API_MAX_UPLOAD_SIZE=104857600  # 100MB
API_CORS_ORIGINS=["https://app.torematrix.com"]
API_TRUSTED_HOSTS=["torematrix.com", "*.torematrix.com"]

# Upload Configuration
UPLOAD_DIR=/data/uploads
MAX_FILE_SIZE=104857600  # 100MB
ALLOWED_EXTENSIONS=pdf,docx,doc,txt,html,xml,json,csv,xlsx,pptx,odt,rtf
ENABLE_VIRUS_SCANNING=true

# Security Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_TRACING=true
JAEGER_ENDPOINT=http://jaeger:14268/api/traces

# Performance Configuration
MAX_CONCURRENT_UPLOADS=100
ENABLE_CACHING=true
CACHE_TTL=3600
ENABLE_COMPRESSION=true
COMPRESSION_LEVEL=6

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3
```

### Secrets Management

Use Kubernetes Secrets or HashiCorp Vault for sensitive configuration:

```bash
# Create secrets
kubectl create secret generic torematrix-secrets \
  --from-literal=database-password='${DB_PASSWORD}' \
  --from-literal=redis-password='${REDIS_PASSWORD}' \
  --from-literal=unstructured-api-key='${UNSTRUCTURED_API_KEY}' \
  --from-literal=jwt-secret-key='${JWT_SECRET_KEY}' \
  --from-literal=encryption-key='${ENCRYPTION_KEY}' \
  --from-literal=aws-access-key='${AWS_ACCESS_KEY_ID}' \
  --from-literal=aws-secret-key='${AWS_SECRET_ACCESS_KEY}'
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace torematrix-prod
```

### 2. Install Dependencies

#### Redis Cluster

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami

helm install redis bitnami/redis \
  --namespace torematrix-prod \
  --set architecture=replication \
  --set auth.enabled=true \
  --set auth.password=${REDIS_PASSWORD} \
  --set replica.replicaCount=3 \
  --set master.persistence.size=20Gi \
  --set replica.persistence.size=20Gi \
  --set metrics.enabled=true
```

#### PostgreSQL Cluster

```bash
helm install postgres bitnami/postgresql \
  --namespace torematrix-prod \
  --set auth.postgresPassword=${DB_PASSWORD} \
  --set auth.database=torematrix \
  --set primary.persistence.size=100Gi \
  --set readReplicas.replicaCount=2 \
  --set readReplicas.persistence.size=100Gi \
  --set metrics.enabled=true
```

### 3. Deploy Application

#### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: torematrix-config
  namespace: torematrix-prod
data:
  TOREMATRIX_ENV: "production"
  TOREMATRIX_LOG_LEVEL: "INFO"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  REDIS_URL: "redis://redis:6379/0"
  # Add other non-sensitive config
```

#### API Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: torematrix-api
  namespace: torematrix-prod
  labels:
    app: torematrix-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: torematrix-api
  template:
    metadata:
      labels:
        app: torematrix-api
    spec:
      containers:
      - name: api
        image: torematrix/ingestion-api:v3.0.0
        ports:
        - containerPort: 8000
        - containerPort: 9090  # Metrics
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: torematrix-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: torematrix-config
              key: REDIS_URL
        envFrom:
        - configMapRef:
            name: torematrix-config
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
        volumeMounts:
        - name: upload-storage
          mountPath: /data/uploads
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: upload-storage
        persistentVolumeClaim:
          claimName: torematrix-upload-pvc
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: torematrix-api-service
  namespace: torematrix-prod
spec:
  selector:
    app: torematrix-api
  ports:
  - name: http
    port: 8000
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP
```

#### Queue Workers Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: torematrix-worker
  namespace: torematrix-prod
  labels:
    app: torematrix-worker
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2
      maxUnavailable: 1
  selector:
    matchLabels:
      app: torematrix-worker
  template:
    metadata:
      labels:
        app: torematrix-worker
    spec:
      containers:
      - name: worker
        image: torematrix/ingestion-worker:v3.0.0
        command: ["python", "-m", "torematrix.worker"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: torematrix-secrets
              key: database-url
        - name: WORKER_CONCURRENCY
          value: "3"
        - name: WORKER_MAX_JOBS
          value: "100"
        envFrom:
        - configMapRef:
            name: torematrix-config
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        volumeMounts:
        - name: upload-storage
          mountPath: /data/uploads
        - name: temp-storage
          mountPath: /tmp
      volumes:
      - name: upload-storage
        persistentVolumeClaim:
          claimName: torematrix-upload-pvc
      - name: temp-storage
        emptyDir:
          sizeLimit: 10Gi
```

### 4. Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: torematrix-ingress
  namespace: torematrix-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://app.torematrix.com"
spec:
  tls:
  - hosts:
    - api.torematrix.com
    secretName: torematrix-tls
  rules:
  - host: api.torematrix.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: torematrix-api-service
            port:
              number: 8000
```

### 5. Storage Configuration

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: torematrix-upload-pvc
  namespace: torematrix-prod
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 500Gi
```

## Monitoring and Observability

### Prometheus Metrics

Deploy Prometheus and Grafana for monitoring:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=${GRAFANA_PASSWORD}
```

### Key Metrics to Monitor

- **API Metrics**:
  - Request rate and latency
  - Error rates
  - Upload throughput
  - Active connections

- **Queue Metrics**:
  - Queue depth
  - Processing rate
  - Worker utilization
  - Failed job rate

- **System Metrics**:
  - CPU and memory usage
  - Disk I/O
  - Network throughput
  - Container restart rate

### Grafana Dashboards

Import pre-built dashboards for:
- TORE Matrix API performance
- Queue worker statistics
- System resource utilization
- Error tracking and alerting

### Logging

Configure centralized logging with ELK stack or similar:

```yaml
# Fluent Bit configuration for log shipping
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
    
    [INPUT]
        Name              tail
        Path              /app/logs/*.log
        Parser            json
        Tag               torematrix.*
        Refresh_Interval  5
    
    [OUTPUT]
        Name  es
        Match *
        Host  elasticsearch.logging.svc.cluster.local
        Port  9200
        Index torematrix-logs
```

## Security

### Network Security

1. **Network Policies**: Restrict traffic between pods
2. **TLS Termination**: Use HTTPS for all external communication
3. **Internal Encryption**: Encrypt Redis and database connections

### Application Security

1. **Authentication**: JWT-based API authentication
2. **Authorization**: Role-based access control (RBAC)
3. **Input Validation**: Strict file type and size validation
4. **Virus Scanning**: Integrate with antivirus for uploaded files

### Security Scanning

```bash
# Container image scanning
trivy image torematrix/ingestion-api:v3.0.0

# Kubernetes security scanning
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml
```

## Backup and Disaster Recovery

### Database Backup

```bash
# Automated PostgreSQL backup
kubectl create job --from=cronjob/postgres-backup postgres-backup-manual
```

### Object Storage Backup

Configure S3 cross-region replication or backup to secondary storage.

### Disaster Recovery Plan

1. **RTO (Recovery Time Objective)**: 2 hours
2. **RPO (Recovery Point Objective)**: 15 minutes
3. **Backup Schedule**: Daily full, hourly incremental
4. **Testing**: Monthly DR drills

## Performance Tuning

### API Server Optimization

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: torematrix-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: torematrix-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Queue Worker Optimization

1. **Worker Scaling**: Use KEDA for queue-based autoscaling
2. **Job Batching**: Process multiple files in single jobs
3. **Resource Limits**: Set appropriate CPU/memory limits

### Database Optimization

1. **Connection Pooling**: Use PgBouncer
2. **Read Replicas**: Distribute read operations
3. **Indexing**: Optimize queries with proper indexes

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check for memory leaks in workers
   - Adjust worker concurrency
   - Monitor garbage collection

2. **Slow Processing**
   - Check Unstructured.io API limits
   - Scale worker replicas
   - Optimize batch sizes

3. **Queue Backlog**
   - Monitor Redis memory usage
   - Add more workers
   - Check for failed jobs

### Debug Commands

```bash
# Check API logs
kubectl logs -n torematrix-prod -l app=torematrix-api --tail=100

# Monitor queue
kubectl exec -n torematrix-prod redis-master-0 -- redis-cli llen document_processing

# Worker status
kubectl get pods -n torematrix-prod -l app=torematrix-worker

# Resource usage
kubectl top pods -n torematrix-prod
```

### Health Checks

```bash
# API health
curl -f https://api.torematrix.com/health

# Queue health
kubectl exec -n torematrix-prod redis-master-0 -- redis-cli ping

# Database health
kubectl exec -n torematrix-prod postgres-primary-0 -- pg_isready
```

## Maintenance

### Rolling Updates

```bash
# Update API
kubectl set image deployment/torematrix-api \
  api=torematrix/ingestion-api:v3.0.1 \
  -n torematrix-prod

# Update Workers (with drain)
kubectl scale deployment torematrix-worker --replicas=0 -n torematrix-prod
kubectl set image deployment/torematrix-worker \
  worker=torematrix/ingestion-worker:v3.0.1 \
  -n torematrix-prod
kubectl scale deployment torematrix-worker --replicas=5 -n torematrix-prod
```

### Database Maintenance

```bash
# Database vacuum (scheduled via CronJob)
kubectl create job --from=cronjob/postgres-vacuum postgres-vacuum-manual
```

### Certificate Renewal

Cert-manager handles automatic certificate renewal for HTTPS.

## Support and Maintenance

### Monitoring Alerts

Set up alerts for:
- High error rates (>5%)
- Queue backlog (>1000 jobs)
- High response times (>5s)
- Low success rates (<95%)
- Resource exhaustion (>90% CPU/Memory)

### Regular Maintenance Tasks

- **Weekly**: Review performance metrics
- **Monthly**: Security updates and patches
- **Quarterly**: Capacity planning review
- **Annually**: Disaster recovery testing

### Support Contacts

- **Production Issues**: support@torematrix.com
- **Documentation**: https://docs.torematrix.com
- **GitHub Issues**: https://github.com/torematrix/ingestion/issues

## Cost Optimization

### Resource Optimization

1. **Right-sizing**: Monitor actual usage vs. allocated resources
2. **Spot Instances**: Use for non-critical workloads
3. **Storage Tiering**: Move old documents to cheaper storage
4. **Auto-scaling**: Reduce costs during low traffic

### Monitoring Costs

Track costs by:
- Service (API, Workers, Database)
- Resource type (CPU, Memory, Storage)
- Environment (Prod, Staging, Dev)

## Conclusion

This deployment guide provides a comprehensive foundation for running TORE Matrix V3 in production. Regular monitoring, maintenance, and optimization are key to ensuring optimal performance and reliability.

For additional support or custom deployment scenarios, contact the TORE Matrix team.