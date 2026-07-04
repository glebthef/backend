from uvicorn import run
from fastapi import FastAPI

from models import engine, Base
from routes import user, sports, events, bets, sessions
app = FastAPI(title="PrimeBet API")


@app.post("/create-all")
async def create_all():
    conn = await engine.connect()
    await conn.run_sync(Base.metadata.create_all)
    await conn.commit()
    await conn.close()
    return {"detail": "Tables created"}


app.include_router(user.router, tags=["Users"])
app.include_router(sports.router, tags=["Sports"])
app.include_router(events.router, tags=["Events"])
app.include_router(bets.router, tags=["Bets"])
app.include_router(sessions.router, tags=["Sessions"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)