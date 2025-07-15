from fastapi import APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Form
from db import db
from pydantic import BaseModel
from bson.objectid import ObjectId
import os
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
        return {"message": "User registered successfully."}
    except Exception as e:
        return {"error": str(e)}


class UserLogin(BaseModel):
    email: str
    password: str

@user_router.post("/login")
def login_user(user: UserLogin, response: Response):
    try:
        # Check if the user exists
        existing_user = db[user_collection].find_one({"email": user.email})
        if not existing_user:
            raise HTTPException(status_code=404, detail="Invalid email or password.")
        # Check if the password matches
        if existing_user.get("password") != user.password:
            raise HTTPException(status_code=404, detail="Invalid email or password.")
        response.set_cookie(key="user_id", value=str(existing_user.get("_id")), httponly=True, secure=True, samesite='none')
        return {"message": "Login successful."}
    except Exception as e:
        return {"error": str(e)}
    
@user_router.get("/logout")
def logout_user(response: Response):
    try:
        response.delete_cookie("user_id")
        return {"message": "Logout successful."}
    except Exception as e:
        return {"error": str(e)}
    


class User(BaseModel):
    id: str
    full_name: str
    email: str


def verify_user(request: Request) -> User:
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated.")
    user = db[user_collection].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")
    user['id'] = str(user['_id']) # Convert ObjectId to string
    user = User(**user)
    return user
    


@user_router.post("/save_image")
async def save_image(
    request: Request,
    image: UploadFile = File(...),
    description: str = Form(...),  # ✅ Receive description from form data
    user: User = Depends(verify_user)
):
    try:
        # Ensure ./storage exists
        os.makedirs("./storage", exist_ok=True)
        print("Storage directory is ready.")

        if not image.filename:
            raise HTTPException(status_code=400, detail="File name is required.")

        # Define file path
        file_location = f"./storage/{user.id + '_' + image.filename}"

        # Save the image to disk
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Find user in the DB
        existing_user = db[user_collection].find_one({"_id": ObjectId(user.id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Create image object
        image_entry = {
            "fname": image.filename,
            "description": description
        }

        # Append to the "images" array field (create it if it doesn't exist)
        db[user_collection].update_one(
            {"_id": ObjectId(user.id)},
            {"$push": {"images": image_entry}}
        )

        return {"message": "Image saved successfully.", "image": image_entry}

    except Exception as e:
        return {"error": str(e)}
    
from fastapi.responses import FileResponse

@user_router.get("/s/{filename}")
async def get_image(
    filename: str,
    user: User = Depends(verify_user)
):
    try:
        # Ensure user exists
        existing_user = db[user_collection].find_one({"_id": ObjectId(user.id)})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Check if the image exists in the user's image list
        images = existing_user.get("images", [])
        match = next((img for img in images if img["fname"] == filename), None)

        if not match:
            raise HTTPException(status_code=404, detail="Image not found for this user.")

        # Construct the full file path
        file_path = f"./storage/{user.id}_{filename}"

        # Check if file exists on disk
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Image file not found on disk.")

        return FileResponse(file_path, media_type="image/*", filename=filename)

    except Exception as e:
        return {"error": str(e)}

@user_router.get("/images")
async def get_all_image_metadata(
    user: User = Depends(verify_user)
):
    try:
        # Fetch the user from the database
        existing_user = db[user_collection].find_one({"_id": ObjectId(user.id)})

        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Retrieve the images list, default to empty list
        images = existing_user.get("images", [])

        return {"images": images}

    except Exception as e:
        return {"error": str(e)}
