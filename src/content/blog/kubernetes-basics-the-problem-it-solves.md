---
title: "Kubernetes basics: the problem it solves and the concepts you need first."
description: "What Kubernetes actually does, the core abstractions you need to understand, and when it's overkill."
pubDate: 2026-02-05
tags: ["Architecture"]
draft: false
---

Kubernetes has a reputation for being complicated. Some of that reputation is deserved -- it is genuinely complex. But the complexity exists to solve real problems, and understanding those problems makes the concepts click.

## The problem Kubernetes solves

You have a containerized application. You need it to:

- Keep running even if a container crashes
- Scale to more instances when traffic increases and scale back down to save cost
- Deploy new versions without downtime
- Spread across multiple servers so a single machine failure doesn't kill everything
- Route traffic to healthy instances only

You could build automation for all of this yourself. Kubernetes is the standard implementation of that automation.

## Core concepts

**Pod:** The smallest deployable unit. A pod wraps one or more containers that share a network namespace and storage volumes. Usually one container per pod, but sidecar patterns use multiple (a main app container plus a logging agent, for example).

Pods are ephemeral. They die and are replaced. Never depend on a pod's IP address or hostname surviving.

**Deployment:** The object that says "I want 3 replicas of this pod, always." The Deployment controller continuously reconciles actual state with desired state. If a pod crashes, the controller creates a replacement. If you change the container image, it rolls out the update gradually.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: my-app:1.2.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

**Service:** Pods come and go with new IP addresses. A Service is a stable network endpoint that routes to whichever pods match its label selector. It gives you a consistent DNS name and load balances across healthy pods.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 8080
```

**Ingress:** A Service exposes pods within the cluster. An Ingress exposes them to the internet, typically with HTTP routing rules (path-based or hostname-based) and TLS termination.

**ConfigMap and Secret:** ConfigMaps store non-sensitive configuration (environment variables, config files). Secrets store sensitive values like database passwords (base64-encoded by default -- for real secret management, integrate with Vault or AWS Secrets Manager).

**Namespace:** Logical partition within a cluster. Teams or environments (staging, prod) can share a cluster while being isolated into separate namespaces.

## The control loop

Everything in Kubernetes is a control loop. A controller watches the cluster state, compares it to the desired state declared in your YAML, and takes action to close the gap. This is why Kubernetes is self-healing: after a crash, the controller notices the deficit and creates a replacement.

You declare *what you want*, not *how to get there*. The controllers handle the how.

## kubectl, the essential commands

```bash
# What's running
kubectl get pods
kubectl get deployments
kubectl get services

# Details on a specific resource
kubectl describe pod web-7d8f9b-xyz

# View logs
kubectl logs web-7d8f9b-xyz
kubectl logs -f web-7d8f9b-xyz  # follow

# Apply configuration from a file
kubectl apply -f deployment.yaml

# Scale manually
kubectl scale deployment web --replicas=5

# Execute a command in a running container
kubectl exec -it web-7d8f9b-xyz -- /bin/sh
```

## When Kubernetes is overkill

Kubernetes has real operational overhead: you need someone who knows it, cluster upgrades take effort, and debugging across pods and nodes is harder than debugging a single server.

It's worth it when:
- You have multiple services that need independent scaling
- You need zero-downtime deployments
- You're already running containers and need orchestration
- Your team is large enough that the operational cost is shared

It's probably overkill for:
- A single-service application with modest traffic
- A team of one or two developers
- Applications that deploy once a month

For smaller projects, a managed service like AWS App Runner, Fly.io, or Railway gives you container orchestration without managing Kubernetes yourself.
