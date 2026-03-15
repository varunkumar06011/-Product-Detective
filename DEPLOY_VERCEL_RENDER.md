# 🚀 One-Click "Zero-Config" Deployment (Fastest)

I have automated the entire infrastructure setup for you. Now you don't need to manually configure settings—it's all in the code!

---

## ⚡ Step 1: Deploy Backend (Render Blueprint)
1.  Log in to [Render.com](https://render.com/).
2.  Go to the **"Blueprints"** section in your dashboard.
3.  Click **"New Blueprint Instance"**.
4.  Connect this repo: `varunkumar06011/-Product-Detective`.
5.  Render will automatically see `render.yaml` and set up:
    -   Your FastAPI Web Service
    -   A dedicated Redis Cache
    -   Environment variables (Secret keys, ports, etc.)
6.  It will ask for a **MONGO_URI**. Please paste your [MongoDB Atlas](https://www.mongodb.com/products/platform/atlas-database) connection string there.

---

## ⚡ Step 2: Deploy Frontend (Vercel)
1.  Log in to [Vercel.com](https://vercel.com/dashboard).
2.  Click **"Add New Project"**.
3.  Connect the same repo.
4.  Vercel will see `vercel.json` and `frontend` folder automatically.
5.  **Environment Variable**: Add `VITE_API_BASE_URL` and paste your new Render URL (e.g., `https://my-api.onrender.com`).
6.  Click **Deploy**!

---

## ⚡ Step 3: Connect
Once Vercel is done, copy your Vercel URL (e.g., `https://my-app.vercel.app`) and add it to the `ALLOWED_ORIGINS` in your Render Service settings.

**CASE CLOSED! Your Premium UI is now live.**
