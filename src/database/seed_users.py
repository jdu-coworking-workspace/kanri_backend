import os
import sys

# Yerni asosiy root papkaga moslash (backend papkasi)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.models.user import User, UserRole
from src.utils.security import get_password_hash

def seed_users():
    db: Session = SessionLocal()
    try:
        users_to_create = [
            {"email": "adminexample1@gmail.com", "full_name": "Admin Example 1", "role": UserRole.ADMIN},
            {"email": "adminexample2@gmail.com", "full_name": "Admin Example 2", "role": UserRole.ADMIN},
            {"email": "staffexample1@gmail.com", "full_name": "Staff Example 1", "role": UserRole.STAFF},
            {"email": "staffexample2@gmail.com", "full_name": "Staff Example 2", "role": UserRole.STAFF},
            {"email": "staffexample3@gmail.com", "full_name": "Staff Example 3", "role": UserRole.STAFF},
            {"email": "staffexample4@gmail.com", "full_name": "Staff Example 4", "role": UserRole.STAFF},
        ]
        
        password = "password123"
        hashed_password = get_password_hash(password)
        
        for user_data in users_to_create:
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing_user:
                new_user = User(
                    email=user_data["email"],
                    password_hash=hashed_password,
                    full_name=user_data["full_name"],
                    role=user_data["role"]
                )
                db.add(new_user)
                print(f"Yaratildi: {user_data['email']} ({user_data['role'].value})")
            else:
                print(f"Mavjud: {user_data['email']}")
                
        db.commit()
        print("Barcha foydalanuvchilar seed qilindi!")
    except Exception as e:
        db.rollback()
        print(f"Xatolik yuz berdi: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()
