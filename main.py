import os

from uvicorn import run
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import user, sports, events, bets, sessions, chat
from dotenv import load_dotenv
load_dotenv()
app = FastAPI(title="PrimeBet API")

# Local dev origins are always allowed; production origin(s) come from the
# environment so the same image/checkout works locally and on the server
# without editing code, e.g. CORS_ORIGINS="http://193.178.158.110".
default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins + extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router, tags=["Users"])
app.include_router(sports.router, tags=["Sports"])
app.include_router(events.router, tags=["Events"])
app.include_router(bets.router, tags=["Bets"])
app.include_router(sessions.router, tags=["Sessions"])
app.include_router(chat.router, tags=["Chat"])

if __name__ == "__main__":
    # 0.0.0.0, not 127.0.0.1: inside a container, binding to loopback only
    # makes the app unreachable through the mapped port from outside it.
    run(app, host="0.0.0.0", port=8000)