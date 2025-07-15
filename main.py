from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from user import user_router

app = FastAPI()

FRONTEND_URL = "http://localhost:5173"


app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # Adjust this to match your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}

app.include_router(user_router)