from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session, joinedload
from . import models, database
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24h para facilitar onboarding

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="restaurantes/login")
oauth2_scheme_motoboy = OAuth2PasswordBearer(tokenUrl="auth/motoboy/login")
oauth2_scheme_admin = OAuth2PasswordBearer(tokenUrl="auth/admin/login")
oauth2_scheme_cozinheiro = OAuth2PasswordBearer(tokenUrl="auth/cozinheiro/login")

def verify_password(plain_password, hashed_password):
    """Verifica senha bcrypt. Aplica strip() para ignorar espaços acidentais."""
    return pwd_context.verify(plain_password.strip(), hashed_password)

def get_password_hash(password):
    """Hash bcrypt da senha. Aplica strip() para ignorar espaços acidentais."""
    return pwd_context.hash(password.strip())

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_restaurante(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        restaurante_id = int(payload.get("sub"))
        role: str = payload.get("role")
        if role != "restaurante":
            raise credentials_exception
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    restaurante = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if restaurante is None:
        raise credentials_exception
    return restaurante


def get_current_motoboy(token: str = Depends(oauth2_scheme_motoboy), db: Session = Depends(database.get_db)):
    """Dependency JWT para autenticação do motoboy."""
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        motoboy_id = int(payload.get("sub"))
        role: str = payload.get("role")
        if role != "motoboy" or motoboy_id is None:
            raise credentials_exception
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    motoboy = db.query(models.Motoboy).options(
        joinedload(models.Motoboy.restaurante)
    ).filter(
        models.Motoboy.id == motoboy_id,
        models.Motoboy.status == 'ativo'
    ).first()
    if motoboy is None:
        raise credentials_exception
    return motoboy


def get_current_admin(token: str = Depends(oauth2_scheme_admin), db: Session = Depends(database.get_db)):
    """Dependency JWT para autenticação do super admin."""
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        admin_id_raw = payload.get("sub")
        role: str = payload.get("role")
        if role != "admin" or admin_id_raw is None:
            raise credentials_exception
        admin_id = int(admin_id_raw)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    admin = db.query(models.SuperAdmin).filter(
        models.SuperAdmin.id == admin_id,
        models.SuperAdmin.ativo == True
    ).first()
    if admin is None:
        raise credentials_exception
    return admin


def get_current_cozinheiro(token: str = Depends(oauth2_scheme_cozinheiro), db: Session = Depends(database.get_db)):
    """Dependency JWT para autenticação do cozinheiro (KDS)."""
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_sub": False})
        cozinheiro_id = int(payload.get("sub"))
        role: str = payload.get("role")
        if role != "cozinheiro" or cozinheiro_id is None:
            raise credentials_exception
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    cozinheiro = db.query(models.Cozinheiro).options(
        joinedload(models.Cozinheiro.restaurante)
    ).filter(
        models.Cozinheiro.id == cozinheiro_id,
        models.Cozinheiro.ativo == True
    ).first()
    if cozinheiro is None:
        raise credentials_exception
    return cozinheiro
