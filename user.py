from fastapi import APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from db import db
from pydantic import BaseModel
from bson.objectid import ObjectId
import os
# load dotenv
from dotenv import load_dotenv
load_dotenv()
import shutil

user_router = APIRouter()
user_router.prefix = "/user"
user_collection = 'user'

@user_router.get("/status")
def get_auth_status():
    return {"status": "User service is running."}

class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str

@user_router.post("/register")
def register_user(user: UserCreate):
    try:
        # Check if the user already exists
        existing_user = db[user_collection].find_one({"email": user.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists with this email.")

        # Insert the new user into the database
        db[user_collection].insert_one(user.model_dump())

        return JSONResponse(
            content={"message": "User registered successfully.", "code": 201},
            status_code=201
        )

    except HTTPException as e:
        return JSONResponse(
            content={"detail": e.detail, "code": e.status_code},
            status_code=e.status_code
        )

    except Exception as e:
        return JSONResponse(
            content={"error": str(e), "code": 500},
            status_code=500
        )


class UserLogin(BaseModel):
    email: str
    password: str

@user_router.post("/login")
def login_user(user: UserLogin):
    try:
        existing_user = db[user_collection].find_one({"email": user.email})
        if not existing_user or existing_user.get("password") != user.password:
            raise HTTPException(status_code=404, detail="Invalid email or password.")

        # ✅ Set cookie
        response = JSONResponse(
            content={"message": "Login successful.", "user_id": str(existing_user.get("_id"))},
            status_code=200
        )
        # response.set_cookie(
        #     key="user_id",
        #     value=str(existing_user.get("_id")),
        #     httponly=True,
        #     secure=False,
        #     samesite='lax'
        # )
        return response
        

    except HTTPException as e:
        # Automatically handled by FastAPI, but you can wrap it like this:
        return JSONResponse(
            content={"detail": e.detail, "code": e.status_code},
            status_code=e.status_code
        )
    except Exception as e:
        # Unexpected server errors
        return JSONResponse(
            content={"error": str(e), "code": 500},
            status_code=500
        )

    
# @user_router.get("/logout")
# def logout_user(response: Response):
#     try:
#         response.delete_cookie("user_id")
#         return {"message": "Logout successful."}
#     except Exception as e:
#         return {"error": str(e)}
    


class User(BaseModel):
    id: str
    full_name: str
    email: str


async def verify_user(request: Request) -> User:
    requset_data = await request.json()
    user_id = requset_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated.")
    user = db[user_collection].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")
    user['id'] = str(user['_id']) # Convert ObjectId to string
    user = User(**user)
    return user


    
from datetime import datetime, timezone

@user_router.post("/save")
async def save_artwork(request: Request, user: User = Depends(verify_user)):
    try:
        data = await request.json()
        art_name = data.get("art_name")
        description = data.get("description")
        prompt = data.get("prompt")
        animal = data.get("animal")
        original_image_url = data.get("original_image_url")
        masked_image_url = data.get("masked_image_url")
        final_image_url = data.get("final_image_url")

        if not all([art_name, description, prompt, animal, original_image_url, masked_image_url, final_image_url]):
            raise HTTPException(status_code=400, detail="All fields are required.")

        artwork_data = {
            "user_id": user.id,
            "art_name": art_name,
            "description": description,
            "prompt": prompt,
            "animal": animal,
            "original_image_url": original_image_url,
            "masked_image_url": masked_image_url,
            "final_image_url": final_image_url,
            "created_at": datetime.now(timezone.utc)
        }

        db['gallery'].insert_one(artwork_data)

        return JSONResponse(
            content={"message": "Artwork saved successfully.", "code": 201},
            status_code=201
        )

    except HTTPException as e:
        return JSONResponse(
            content={"detail": e.detail, "code": e.status_code},
            status_code=e.status_code
        )
    except Exception as e:
        return JSONResponse(
            content={"error": str(e), "code": 500},
            status_code=500
        )
    
@user_router.get("/gallery/{user_id}")
async def get_user_gallery(user_id: str):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated.")
        user = db[user_collection].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="User not authenticated.")
        
        gallery_items = list(db['gallery'].find({"user_id": user_id}))
        
        print(gallery_items[0].get("created_at"))
        for item in gallery_items:
            item['_id'] = str(item['_id'])
            item['created_at'] = str(item['created_at'].date().isoformat()
)
        return JSONResponse(
            content={"gallery": gallery_items, "code": 200},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"error": str(e), "code": 500},
            status_code=500
        )