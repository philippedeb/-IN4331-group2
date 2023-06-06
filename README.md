# Web-scale Data Management Project
Developed by IN4331 Group 2, containing the following members:
* Enrique Barba Roque
* Philippe de Bekker
* Jokubas de Kort
* Arjan Hasami
* Simcha Vos

#### Repository Status
[![Latest Tag](https://img.shields.io/github/tag/philippedeb/IN4331-group2.svg)](https://github.com/philippedeb/IN4331-group2/tags) [![Latest Commit](https://img.shields.io/github/last-commit/philippedeb/IN4331-group2.svg)](https://github.com/philippedeb/IN4331-group2/commits/main)

> Note: This repository is a fork of the [wdm-project-template](https://github.com/delftdata/wdm-project-template).

## Project description

## Project structure

- `env`
  Folder containing the Redis env variables for the docker-compose deployment
- `helm-config`
  Helm chart values for Redis and ingress-nginx
- `k8s`
  Folder containing the kubernetes deployments, apps and services for the ingress, order, payment and stock services.
- `order`
  Folder containing the order application logic and dockerfile.
- `payment`
  Folder containing the payment application logic and dockerfile.

- `stock`
  Folder containing the stock application logic and dockerfile.

- `test`
  Folder containing some basic correctness tests for the entire system. (Feel free to enhance them)

- `wdm-chart`
  Folder containing a Helm Chart that deploys the full app stack (databases + microservices)
- `wdm-reactive-chart`
  Chart for the second model of the app, implementing the reactive architecture with Celery and RabbitMQ


## Deployment types:

### Helm Chart
To deploy using the provided Helm chart, first add the Bitnami repo to your Helm installation:

```console
helm repo add bitnami https://charts.bitnami.com/bitnami
```

Then, open a terminal in the `wdm-reactive-chart` folder. You can modify the parameters in the values.yaml file as you see fit. Then run

 ```console
helm dependency update
helm dependency build
helm install [RELEASE] .
```

### docker-compose (local development)

Enter the database URL and password in the .env files for each corresponding service. Start a new virtual environment and run `docker-compose up --build` to start the gateway and its services.

#### Example HTTP request

`[POST]: localhost:8000/orders/create/1`

**_Requirements:_** You need to have docker and docker-compose installed on your machine.

### minikube (local k8s cluster)

This setup is for local k8s testing to see if your k8s config works before deploying to the cloud.
First deploy your database using helm by running the `deploy-charts-minikube.sh` file (in this example the DB is Redis
but you can find any database you want in https://artifacthub.io/ and adapt the script). Then adapt the k8s configuration files in the
`\k8s` folder to match your system and then run `kubectl apply -f .` in the k8s folder.

**_Requirements:_** You need to have minikube (with Ingress enabled) and helm installed on your machine.

### kubernetes cluster (managed k8s cluster in the cloud)

Similarly to the `minikube` deployment but run the `deploy-charts-cluster.sh` in the helm step to also install an ingress to the cluster.

**_Requirements:_** You need to have access to kubectl of a k8s cluster.
