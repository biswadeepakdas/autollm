# Deploy AutoLLM to Railway

Total time: ~10 minutes

---

## Step 1: Push to GitHub (2 min)

Open Terminal on your Mac and run:

```bash
cd ~/Desktop/AutoLLM

git init
git branch -m main
git add -A
git commit -m "Initial commit: AutoLLM SaaS — full stack"

# Create repo on GitHub (install gh CLI first: brew install gh)
gh auth login
gh repo create autollm --public --source=. --push
```

Or create the repo manually at https://github.com/new, then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/autollm.git
git push -u origin main
```

---

## Step 2: Set up Railway (5 min)

1. Go to https://railway.app and sign in with GitHub
2. Click **"New Project"** → **"Deploy from GitHub Repo"**
3. Select your `autollm` repo

### Add Postgres

- Click **"+ New"** → **"Database"** → **"PostgreSQL"**
- Railway auto-creates the `DATABASE_URL` variable

### Add Redis

- Click **"+ New"** → **"Database"** → **"Redis"**
- Railway auto-creates the `REDIS_URL` variable

### Configure Backend Service

- Click **"+ New"** → **"GitHub Repo"** → select `autollm`
- In service settings:
  - **Root Directory:** `backend`
  - **Builder:** Dockerfile
- Go to the **Variables** tab and add:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<generate with: openssl rand -hex 32>
FRONTEND_URL=https://<your-frontend>.up.railway.app
BACKEND_URL=https://<your-backend>.up.railway.app
GOOGLE_CLIENT_ID=<from Google Cloud Console, optional>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console, optional>
GOOGLE_REDIRECT_URI=https://<your-backend>.up.railway.app/api/auth/google/callback
```

> **Tip:** Use Railway's variable references like `${{Postgres.DATABASE_URL}}` to auto-link.
> For the `DATABASE_URL`, append `+asyncpg` after `postgresql` since we use async:
> Change `postgresql://...` to `postgresql+asyncpg://...`

### Configure Frontend Service

- Click **"+ New"** → **"GitHub Repo"** → select `autollm`
- In service settings:
  - **Root Directory:** `frontend`
  - **Builder:** Nixpacks
- Go to the **Variables** tab and add:

```
NEXT_PUBLIC_API_URL=https://<your-backend>.up.railway.app
```

### Generate Domains

For each service (backend and frontend), go to **Settings** → **Networking** → **Generate Domain**.

Update the `FRONTEND_URL`, `BACKEND_URL`, and `GOOGLE_REDIRECT_URI` variables with the actual domains Railway gives you.

---

## Step 3: Deploy (automatic)

Railway auto-deploys when you push to `main`. After setting the variables, click **"Deploy"** on each service. Wait 2-3 minutes for both to build.

---

## Step 4: Verify

1. Visit your **backend** domain + `/docs` — you should see FastAPI's Swagger UI
2. Visit your **backend** domain + `/health` — should return `{"status": "ok"}`
3. Visit your **frontend** domain — you should see the AutoLLM login page

---

## Optional: Google OAuth Setup

To enable "Continue with Google":

1. Go to https://console.cloud.google.com
2. Create a project (or use existing)
3. Go to **APIs & Services** → **Credentials** → **Create OAuth Client ID**
4. Application type: **Web application**
5. Authorized redirect URI: `https://<your-backend>.up.railway.app/api/auth/google/callback`
6. Copy Client ID and Client Secret into Railway env vars

---

## Cost

Railway free tier gives you $5/month credit, which is enough to run this for testing. For production:

- **Hobby plan:** $5/month (covers small traffic)
- **Pro plan:** $20/month (for real users, includes autoscaling)

Postgres and Redis are included in the plan pricing.

---

## Troubleshooting

**Backend won't start:** Check the `DATABASE_URL` has `+asyncpg` in it. Railway's default is `postgresql://` but we need `postgresql+asyncpg://`.

**Frontend shows errors:** Make sure `NEXT_PUBLIC_API_URL` points to the backend domain with `https://`.

**CORS errors:** Update `FRONTEND_URL` in backend env vars to match the exact frontend domain Railway assigned.

**OAuth not working:** Make sure `GOOGLE_REDIRECT_URI` matches exactly what's in Google Cloud Console.
