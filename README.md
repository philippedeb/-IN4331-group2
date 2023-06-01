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

Basic project structure with Python's Flask and Redis.
**You are free to use any web framework in any language and any database you like for this project.**

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

## Deployment types:

### docker-compose (local development)

Enter the database URL and password in the .env files for each corresponding service. Start a new virtual environment and run `docker-compose up --build` to start the gateway and its services.

#### Example HTTP request

`[POST]: localhost:8000/orders/create/1`

**_Requirements:_** You need to have docker and docker-compose installed on your machine.

### minikube (local k8s cluster)

This setup is for local k8s testing to see if your k8s config works before deploying to the cloud.
First deploy your database using helm by running the `deploy-charts-minikube.sh` file (in this example the DB is Redis
but you can find any database you want in https://artifacthub.io/ and adapt the script). Then adapt the k8s configuration files in the
`\k8s` folder to match your system and then run `kubectl apply -f .` in the k8s folder. Then run minikube tunnel to expose the services on port 80.

**_Requirements:_** You need to have minikube (with Ingress enabled) and helm installed on your machine.

### kubernetes cluster (managed k8s cluster in the cloud)

Similarly to the `minikube` deployment but run the `deploy-charts-cluster.sh` in the helm step to also install an ingress to the cluster.

**_Requirements:_** You need to have access to kubectl of a k8s cluster.

## Testing
### Setup 
* Install python 3.8 or greater (tested with 3.11)
* Install the required packages using: `pip install -r requirements.txt`
````
Note: For Windows users you might also need to install pywin32
````

### Running Stress Test
* Open terminal and navigate to the `locustfile.py` folder
* Run script: `locust -f locustfile.py --host="localhost"`
* Go to `http://localhost:8089/`


### Stress Test Kubernetes 

The tasks are the same as the `stress-test` and can be found in `stress-test-k8s/docker-image/locust-tasks`.
This folder is adapted from Google's [Distributed load testing using Google Kubernetes Engine](https://cloud.google.com/architecture/distributed-load-testing-using-gke)
and original repo is [here](https://github.com/GoogleCloudPlatform/distributed-load-testing-using-kubernetes). 
Detailed instructions are in Google's blog post.
If you want to deploy locally or with a different cloud provider the lines that you have to change are:
1) In `stress-test-k8s/kubernetes-config/locust-master-controller.yaml` line 34 you could add a dockerHub image that you
published yourself and in line 39 set `TARGET_HOST` to the IP of your API gateway. 
2) Change the same configuration parameters in the `stress-test-k8s/kubernetes-config/locust-worker-controller.yaml`


### Running Consistency Test
* Run script `run_consistency_test.py`

In the provided consistency test we first populate the databases with 100 items with 1 stock that costs 1 credit 
and 1000 users that have 1 credit. 

Then we concurrently send 1000 checkouts of 1 item with random user/item combinations.
If everything goes well only 10% of the checkouts will succeed, and the expected state should be 0 stock across all 
items and 100 credits subtracted across different users.  

Finally, the measurements are done in two phases:
1) Using logs to see whether the service sent the correct message to the clients
2) Querying the database to see if the actual state remained consistent

