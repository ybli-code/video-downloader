"""
认证 API: 注册 / 登录 / 刷新令牌 / 用户信息
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from core.deps import get_current_user
from models.user import User, UserRole

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ── 请求模型 ──

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    account: str = Field(..., description="用户名或邮箱")
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── 端点 ──

@router.post("/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "用户名已存在")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "邮箱已注册")

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=UserRole.FREE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})

    return {
        "success": True,
        "user": user.to_dict(),
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(
        (User.username == req.account) | (User.email == req.account)
    ).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已禁用")

    user.last_login_at = datetime.utcnow()
    db.commit()

    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})

    return {
        "success": True,
        "user": user.to_dict(),
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    """刷新访问令牌"""
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "刷新令牌无效或已过期")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(401, "用户不存在或已禁用")

    access = create_access_token({"sub": str(user.id)})
    return {"access_token": access, "token_type": "bearer"}


@router.get("/me")
async def get_profile(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {"user": user.to_dict()}
