# FORGEPULSE: Cloud & Edge Deployment Guide

## 1. Local Deployment (Docker Compose)

```bash
# Start full stack: Postgres, Mosquitto, FastAPI backend, Simulator, React frontend
docker compose --profile full up --build -d
```

---

## 2. Production Cloud Architecture

### Frontend (Vercel):
1. Connect GitHub repository to Vercel.
2. Root Directory: `frontend`
3. Build Command: `npm run build`
4. Output Directory: `dist`
5. Environment Variables:
   - `VITE_API_BASE_URL`: `https://forgepulse-api.onrender.com/api/v1`

### Backend & Database (Render):
1. Create a **PostgreSQL Database** on Render.
2. Create a **Web Service** on Render pointing to `backend/Dockerfile`.
3. Environment Variables:
   - `APP_ENV`: `production`
   - `DEBUG`: `false`
   - `DATABASE_URL`: *(Render internal Postgres connection string)*
   - `MQTT_BROKER_HOST`: *(Managed HiveMQ / EMQX Cloud broker URL)*
   - `MQTT_BROKER_PORT`: `8883`
   - `MQTT_USE_TLS`: `true`
   - `MQTT_USERNAME`: *(Broker credentials)*
   - `MQTT_PASSWORD`: *(Broker credentials)*
   - `CORS_ORIGINS`: `https://forgepulse.vercel.app`
