from fastapi import APIRouter, Depends, Form, HTTPException
from pydantic import BaseModel

from auth.utils import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from config import users_collection

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),  # "candidate" or "recruiter"
):
    # Validate role
    if role not in ["candidate", "recruiter"]:
        raise HTTPException(
            status_code=400, detail="Invalid role. Must be 'candidate' or 'recruiter'."
        )

    # Check if user already exists
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="User already exists")

    # Hash password
    hashed_pw = get_password_hash(password)

    # Insert user record
    user_doc = {
        "name": name,
        "email": email,
        "password": hashed_pw,
        "role": role,
    }
    users_collection.insert_one(user_doc)

    return {
        "message": "User registered successfully",
        "name": name,
        "email": email,
        "role": role,
    }


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
):
    user = users_collection.find_one({"email": email})
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(
        {
            "_id": str(user["_id"]),
            "name": str(user["name"]),
            "email": user["email"],
            "role": user["role"],
        }
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def read_users_me(current_user=Depends(get_current_user)):
    return {
        "email": current_user.get("email"),
        "role": current_user.get("role"),
        "id": str(current_user["_id"]),
        "name": str(current_user["name"]),
    }


@router.get("/protected")
def protected_route(current_user=Depends(get_current_user)):
    return {
        "message": f"Hello, {current_user['email']}! Access granted.",
        "role": current_user.get("role"),
    }
