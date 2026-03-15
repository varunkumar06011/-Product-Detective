# Professional Deployment Guide (Vercel + Render)

This guide shows you how to host your **Premium React UI** on Vercel and your **FastAPI Backend** on Render. This is the professional setup to keep your high-fidelity "Dossier" design live.

---

## 1. Backend: Deploy on Render 🚀

1.  Log in to [Render.com](https://render.com/).
2.  Create a **New Web Service**.
3.  Connect your GitHub repo: `varunkumar06011/-Product-Detective`.
4.  Set the following:
    -   **Root Directory**: Leave blank (repo root).
    -   **Runtime**: `Python 3`.
    -   **Build Command**: `pip install -r backend/requirements.txt`.
    -   **Start Command**: `./backend/start.sh`.
5.  **Environment Variables**:
    -   `PYTHONPATH`: `backend`
    -   `ALLOWED_ORIGINS`: `https://your-vercel-app-url.vercel.app` (Add yours later).
    -   `PORT`: `8000`
    -   `SECRET_KEY`: `<generate-a-random-string>`

---

## 2. Frontend: Deploy on Vercel 🎨

1.  Log in to [Vercel.com](https://vercel.com/).
2.  Create a **New Project**.
3.  Connect the same GitHub repo.
4.  Set the following:
    -   **Root Directory**: `frontend`.
    -   **Framework Preset**: `Vite`.
5.  **Environment Variables**:
    -   `VITE_API_BASE_URL`: `https://your-render-app-url.onrender.com` (Get this from your Render dashboard).
6.  Click **Deploy**!

---

## 3. Connect the Dots 🔗

1.  Once Vercel gives you an app URL (e.g., `https://pd-ui.vercel.app`), go back to your **Render Dashboard**.
2.  Update the `ALLOWED_ORIGINS` environment variable to include your Vercel URL.
3.  Restart your Render service.

**Your Premium UI is now live at your Vercel URL!**
