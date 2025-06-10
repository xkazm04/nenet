## Local run
```bash
git clone https://github.com/parta004/nene
pip install -r requirements.txt
uvicorn main:app --reload
```

### Docker
```bash
cd nene
docker build -t nene:latest .
docker run -d -p 8000:8000 nene:latest .
# docker run -d -p 8000:8000 --name nene-container nene:latest - to test service is running
# Verify ffmpeg
docker exec -it nene-container /bin/bash
ffmpeg -version
docker stop nene-container
docker rm nene-container
```

## Deployment
Instruction fro Google Cloud - will be used for production at the end of the hackathon

```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com
# With variables
gcloud run deploy YOUR_SERVICE_NAME --source . --region YOUR_REGION \
  --set-env-vars SUPABASE_URL="your_value",SUPABASE_SERVICE_ROLE_KEY="your_key",OPENAI_API_KEY="your_openai_key"

```
- Replace YOUR_SERVICE_NAME with a name for your service (e.g., storyteller-api).
- Replace YOUR_REGION with the Google Cloud region where you want to deploy (e.g., us-central1, europe-west1).
- --allow-unauthenticated makes your service publicly accessible. If you need to restrict access, you can remove this flag and configure IAM permissions.

During the deployment, gcloud will use Cloud Build to build your Docker image from the Dockerfile and then deploy it to Cloud Run.


## Procedure
- Gemini search basic - Found from wiki
- Firecrawl - second option