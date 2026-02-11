from fastapi import APIRouter, Depends
from app.auth import get_current_user

router = APIRouter(
    prefix="",
    tags=["users"],
)


@router.get("/me")
def read_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }
