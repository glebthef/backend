from uvicorn import run
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import user, sports, events, bets, sessions

app = FastAPI(title="PrimeBet API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router, tags=["Users"])
app.include_router(sports.router, tags=["Sports"])
app.include_router(events.router, tags=["Events"])
app.include_router(bets.router, tags=["Bets"])
app.include_router(sessions.router, tags=["Sessions"])

if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8000)