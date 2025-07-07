# Deploying Garak Dashboard to Google Kubernetes Engine (GKE)

This guide provides step-by-step instructions for deploying the Garak Dashboard to a GKE cluster. This setup uses Google Cloud Storage (GCS) for persistent storage of job data and reports, which is the recommended approach for a scalable and stateless deployment.

## Overview

The deployment consists of the following Kubernetes resources:
-   A **Deployment** to run the Garak Dashboard container.
-   A **Service** of type `LoadBalancer` to expose the dashboard to the internet.

The application is configured to use **Workload Identity** to securely access a GCS bucket without needing to manage service account keys.

## Prerequisites

1.  **Google Cloud SDK (`gcloud`)**: Ensure you have `gcloud` installed and authenticated.
    ```bash
    gcloud auth login
    gcloud config set project YOUR_GCP_PROJECT_ID
    ```
2.  **`kubectl`**: Ensure you have the Kubernetes command-line tool installed.
    ```bash
    gcloud components install kubectl
    ```
3.  **GKE Cluster**: A running GKE cluster with Workload Identity enabled. If you are creating a new cluster, you can enable it with:
    ```bash
    gcloud container clusters create YOUR_CLUSTER_NAME \
        --workload-pool=YOUR_GCP_PROJECT_ID.svc.id.goog \
        --zone=YOUR_GCP_ZONE
    ```
4.  **Enabled APIs**: Make sure the following APIs are enabled in your GCP project:
    -   Kubernetes Engine API
    -   Cloud Storage API
    -   Container Registry API or Artifact Registry API
5.  **Docker Image**: The Garak Dashboard Docker image must be built and pushed to a registry accessible by your GKE cluster (e.g., GCR or Artifact Registry).
    ```bash
    # Make sure you have updated requirements.txt to include google-cloud-storage
    # From the root of the 'garak' repository:
    gcloud builds submit --tag gcr.io/YOUR_GCP_PROJECT_ID/garak-dashboard:latest ./dashboard
    ```

## Configuration Steps

### 1. Create a GCS Bucket

This bucket will store all job data and reports.

```bash
export GCS_BUCKET_NAME="garak-dashboard-storage-$(gcloud config get-value project)"
gsutil mb gs://${GCS_BUCKET_NAME}
```

### 2. Configure Workload Identity

Workload Identity is the recommended way to allow your GKE application to access GCP services securely.

#### a. Create a Kubernetes Service Account (KSA)

Create a file named `service-account.yaml` with the following content:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: garak-dashboard-sa
  namespace: default
```

Apply it to your cluster:
```bash
kubectl apply -f service-account.yaml
```

#### b. Create a Google Service Account (GSA)

This service account will be used by the application to interact with GCS.

```bash
export GSA_NAME="garak-dashboard-gsa"
gcloud iam service-accounts create ${GSA_NAME} \
    --display-name="Garak Dashboard GSA"
```

#### c. Grant GCS Permissions to the GSA

Allow the GSA to read and write objects in your GCS bucket.

```bash
export GSA_EMAIL=$(gcloud iam service-accounts list --filter="displayName:'Garak Dashboard GSA'" --format='value(email)')

gsutil iam ch serviceAccount:${GSA_EMAIL}:objectAdmin gs://${GCS_BUCKET_NAME}
```

#### d. Bind the GSA to the KSA

Create an IAM policy binding between the GSA and the KSA. This allows the Kubernetes service account to impersonate the Google service account.

```bash
gcloud iam service-accounts add-iam-policy-binding ${GSA_EMAIL} \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:$(gcloud config get-value project).svc.id.goog[default/garak-dashboard-sa]"
```

### 3. Update Kubernetes Manifests

#### a. `deployment.yaml`

Modify your `deployment.yaml` to use Workload Identity and the GCS bucket.

-   Set the `serviceAccountName` to the KSA you created (`garak-dashboard-sa`).
-   Add the `GCS_BUCKET_NAME` environment variable.
-   Remove the `PersistentVolumeClaim` volume and volume mounts.
-   Add an `emptyDir` volume for temporary storage that `garak` can write to before the app uploads the results to GCS.

Here is an example of what the updated `deployment.yaml` should look like:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: garak-dashboard-deployment
  labels:
    app: garak-dashboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: garak-dashboard
  template:
    metadata:
      labels:
        app: garak-dashboard
    spec:
      serviceAccountName: garak-dashboard-sa # Important for Workload Identity
      containers:
      - name: garak-dashboard
        image: gcr.io/YOUR_GCP_PROJECT_ID/garak-dashboard:latest
        ports:
        - containerPort: 8080
        env:
        - name: PORT
          value: "8080"
        - name: GCS_BUCKET_NAME
          value: "YOUR_GCS_BUCKET_NAME" # e.g., garak-dashboard-storage-your-project-id
        - name: DATA_DIR
          value: "/app/data" # Temporary storage
        - name: REPORT_DIR
          value: "/app/reports" # Temporary storage
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
        volumeMounts:
        - name: temp-storage
          mountPath: /app/data
        - name: temp-storage
          mountPath: /app/reports
      volumes:
      - name: temp-storage
        emptyDir: {}
```
**Note:** Ensure your `app.py` has been updated to use the `google-cloud-storage` library to read/write from the GCS bucket specified by `GCS_BUCKET_NAME`. The `pvc.yaml` file is no longer needed.

#### b. `service.yaml`

The `service.yaml` file exposes the dashboard. No changes are needed here.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: garak-dashboard-service
spec:
  selector:
    app: garak-dashboard
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
```

## Deployment

Apply the manifests to your GKE cluster:

```bash
# First, the service
kubectl apply -f service.yaml

# Then, the deployment
kubectl apply -f deployment.yaml
```

## Accessing the Dashboard

Wait for the deployment to complete and for the `LoadBalancer` to get an external IP address.

```bash
kubectl get service garak-dashboard-service --watch
```

Once an `EXTERNAL-IP` is assigned, you can access the dashboard by navigating to `http://<EXTERNAL-IP>` in your browser.

## Troubleshooting

-   **Pod in `Error` or `CrashLoopBackOff` state**: Check the pod logs for errors.
    ```bash
    kubectl logs <pod-name>
    ```
-   **Permission Denied errors**: Ensure Workload Identity is configured correctly and the GSA has `objectAdmin` permissions on the GCS bucket.
-   **ImagePullBackOff**: Make sure your GKE cluster has permission to pull images from your container registry.
