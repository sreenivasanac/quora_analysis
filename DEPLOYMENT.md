# Deployment Guide (Option A): Host Nginx + systemd

This server deploys Quora Analysis as:

- **Backend API**: systemd service (`quora-api.service`) on port **8003**
- **Frontend**: static build served by host Nginx from `/var/www/quora_analysis`
- **TLS**: host `certbot` -> `/etc/letsencrypt`

## Prerequisites
- Nginx installed on host
- Certbot installed on host
- Backend service running (see `quora-api.service`)

## Repo Templates

- Host Nginx vhost template:
  - `deploy/nginx/quora-analysis.pragnyalabs.com.conf.template`

## Local Development

### 1. Run Flask Backend (Port 5000)
```bash
cd visualization
python visualization_backend.py
```

### 2. Run React Frontend (Port 3000)
```bash
cd visualization/visualization_frontend
npm start
```

The React app will automatically connect to the Flask backend on localhost:5000.

## Production Deployment (Host)

### 1. Backend (systemd)

Install the service:

```bash
sudo cp quora-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable quora-api
sudo systemctl restart quora-api
sudo systemctl status quora-api
```

### 2. Frontend build

The frontend lives at:

- `visualization/visualization_frontend/`

Build output is:

- `visualization/visualization_frontend/build/`

The deploy script builds and publishes it automatically to:

- `/var/www/quora_analysis`

### 3. Nginx vhost

Create:

`/etc/nginx/sites-available/quora-analysis.pragnyalabs.com.conf`

Copy from repo template:

`deploy/nginx/quora-analysis.pragnyalabs.com.conf.template`

Enable and reload:

```bash
sudo ln -sf /etc/nginx/sites-available/quora-analysis.pragnyalabs.com.conf /etc/nginx/sites-enabled/quora-analysis.pragnyalabs.com.conf
sudo nginx -t
sudo systemctl reload nginx
```

### 4. TLS

```bash
sudo mkdir -p /var/www/certbot
sudo chown -R www-data:www-data /var/www/certbot

sudo certbot certonly --webroot -w /var/www/certbot -d quora-analysis.pragnyalabs.com
sudo nginx -t
sudo systemctl reload nginx
```

### Architecture
- **Frontend**: static files served by Nginx
- **Backend**: gunicorn via systemd on port 8003
- **Database**: SQLite (as configured in this repo)

## API Endpoints (Both Local & Production)
- `/api/health` - Health check
- `/api/timestamps` - Get timestamps for date range
- `/api/stats` - Get overall statistics
- `/api/timestamps/all` - Get all timestamps

## File Structure
```
project/
├── api/                    # Vercel serverless functions
│   ├── timestamps.py
│   ├── stats.py
│   └── health.py
├── utils/                  # Shared business logic
│   ├── database.py
│   └── timezone_utils.py
├── visualization/
│   ├── visualization_backend.py    # Flask app (local dev)
│   └── visualization_frontend/     # React app
├── requirements.txt        # Python dependencies
└── vercel.json            # Vercel configuration
```

## Cost
- **Vercel**: Free tier (sufficient for your use case)
- **Supabase**: Free tier (500MB database)
- **Total**: $0/month

## Benefits of This Setup
- ✅ Works locally with Flask + React
- ✅ Deploys to Vercel serverless functions
- ✅ Same codebase for both environments
- ✅ No code duplication
- ✅ Easy development workflow