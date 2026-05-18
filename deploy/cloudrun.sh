#!/usr/bin/env bash
# One-shot Cloud Run deploy for healthcare-ai-data-engineer.
# Usage:  bash deploy/cloudrun.sh
#
# Prereqs (one-time per project, run from project root):
#   gcloud config set project $GCP_PROJECT
#   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
#
# Cost: $0 idle (scale-to-zero), ~$0.40 per 1k requests at 1Gi/1CPU.

set -euo pipefail

# ── Auth: use bchan-genai-deploy SA if its key is present ──
# Avoids the daily `gcloud auth login` browser dance. One-time setup:
#   gcloud iam service-accounts create bchan-genai-deploy
#   + 5 deploy roles · key at ~/.config/secrets/bchan-genai-deploy.json
SA_KEY="$HOME/.config/secrets/bchan-genai-deploy.json"
if [[ -f "$SA_KEY" ]]; then
  SA_EMAIL="bchan-genai-deploy@bchan-genai-lab.iam.gserviceaccount.com"
  gcloud auth activate-service-account --key-file="$SA_KEY" --quiet >/dev/null 2>&1 || true
  export CLOUDSDK_CORE_ACCOUNT="$SA_EMAIL"
  echo "[auth] using SA $SA_EMAIL"
fi

PROJECT="${GCP_PROJECT:-bchan-genai-lab}"
REGION="${GCP_REGION:-us-west1}"
SERVICE="${SERVICE_NAME:-healthcare-ai-data}"
REPO="cloud-run-source-deploy"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:latest"

echo "[1/3] Building image → ${IMAGE}"
# --async pattern: deploy SA can't stream Cloud Build logs (the streamer
# requires project Viewer/Owner OAuth-style perms that don't grant cleanly
# to a deploy SA). The build itself runs fine — we just poll for status.
BUILD_ID=$(gcloud builds submit --tag "$IMAGE" --project "$PROJECT" \
  --async --format="value(id)" .)
echo "[1/3]   build id: $BUILD_ID — polling for completion..."
while true; do
  STATUS=$(gcloud builds describe "$BUILD_ID" --project "$PROJECT" \
    --format="value(status)")
  case "$STATUS" in
    SUCCESS) echo "[1/3]   ✅ build SUCCESS"; break ;;
    WORKING|QUEUED|PENDING) sleep 5 ;;
    *) echo "[1/3]   ❌ build $STATUS"; exit 1 ;;
  esac
done

echo "[2/3] Deploying to Cloud Run..."
gcloud run deploy "$SERVICE" \
    --image "$IMAGE" \
    --region "$REGION" \
    --project "$PROJECT" \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --min-instances 0 \
    --max-instances 3

echo "[3/3] Service URL:"
gcloud run services describe "$SERVICE" \
    --region "$REGION" --project "$PROJECT" \
    --format='value(status.url)'
