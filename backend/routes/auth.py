from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)
from pathlib import Path
import io
PROFILE_DIR = Path(
    "data/profile_pictures"
)

PROFILE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

MAX_PROFILE_SIZE = 5 * 1024 * 1024

CLOUDINARY_FOLDER = "acadai/profile_pictures"


def _cloudinary_public_id(student_id: str) -> str:
    return f"{CLOUDINARY_FOLDER}/{student_id}"


def _configure_cloudinary() -> None:
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.getenv("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "").strip()

    if not cloud_name or not api_key or not api_secret:
        raise RuntimeError(
            "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET."
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


def _delete_cloudinary_picture(student_id: str) -> bool:
    try:
        _configure_cloudinary()

        result = cloudinary.uploader.destroy(
            _cloudinary_public_id(student_id),
            resource_type="image",
            invalidate=True,
        )

        return result.get("result") in {"ok", "not found"}

    except Exception:
        traceback.print_exc()
        return False
from pydantic import BaseModel, EmailStr
from datetime import datetime
import hashlib
import hmac
import secrets
import os
import re
import traceback
import json

import cloudinary
import cloudinary.uploader
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import timedelta

from backend.database import get_connection


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        310000
    )

    return (
        salt.hex()
        + ":"
        + password_hash.hex()
    )


def verify_password(
    password: str,
    stored_password: str
) -> bool:

    try:

        salt_hex, hash_hex = (
            stored_password.split(":")
        )

        salt = bytes.fromhex(salt_hex)

        stored_hash = bytes.fromhex(hash_hex)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            310000
        )

        return hmac.compare_digest(
            password_hash,
            stored_hash
        )

    except (ValueError, TypeError):

        return False


# ============================================================
# REQUEST MODELS
# ============================================================

class SignupRequest(BaseModel):

    student_id: str
    full_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):

    student_id: str
    password: str


class UpdatePasswordRequest(BaseModel):

    student_id: str
    current_password: str
    new_password: str


class UpdateNameRequest(BaseModel):

    student_id: str
    current_password: str
    full_name: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str


# ============================================================
# SIGNUP
# ============================================================

@router.post("/signup")
def signup(request: SignupRequest):

    student_id = (
        request.student_id
        .strip()
        .upper()
    )

    full_name = (
        request.full_name
        .strip()
    )

    email = (
        str(request.email)
        .strip()
        .lower()
    )

    password = request.password


    if not student_id:

        return {
            "success": False,
            "error": "Student ID is required."
        }


    if not full_name:

        return {
            "success": False,
            "error": "Full name is required."
        }


    if len(password) < 6:

        return {
            "success": False,
            "error": "Password must be at least 6 characters."
        }


    connection = get_connection()

    cursor = connection.cursor()


    # --------------------------------------------------------
    # CHECK STUDENT ID
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE student_id = ?
        """,
        (student_id,)
    )

    existing_student = cursor.fetchone()


    if existing_student:

        connection.close()

        return {
            "success": False,
            "error": "Student ID already registered."
        }


    # --------------------------------------------------------
    # CHECK EMAIL
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,)
    )

    existing_email = cursor.fetchone()


    if existing_email:

        connection.close()

        return {
            "success": False,
            "error": "Email already registered."
        }


    # --------------------------------------------------------
    # HASH PASSWORD
    # --------------------------------------------------------

    password_hash = hash_password(
        password
    )


    # --------------------------------------------------------
    # CREATE ACCOUNT
    # --------------------------------------------------------

    cursor.execute(
        """
        INSERT INTO users (
            student_id,
            full_name,
            email,
            password_hash,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            student_id,
            full_name,
            email,
            password_hash,
            datetime.now().isoformat()
        )
    )


    connection.commit()

    connection.close()


    return {
        "success": True,
        "message": "Account created successfully.",
        "student_id": student_id
    }


# ============================================================
# LOGIN
# ============================================================

@router.post("/login")
def login(request: LoginRequest):

    student_id = (
        request.student_id
        .strip()
        .upper()
    )

    password = request.password


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            student_id,
            full_name,
            email,
            password_hash
        FROM users
        WHERE student_id = ?
        """,
        (student_id,)
    )


    user = cursor.fetchone()

    connection.close()


    if not user:

        return {
            "success": False,
            "error": "Invalid Student ID or password."
        }


    if not verify_password(
        password,
        user["password_hash"]
    ):

        return {
            "success": False,
            "error": "Invalid Student ID or password."
        }


    return {
        "success": True,
        "message": "Login successful.",

        "student": {

            "student_id":
                user["student_id"],

            "full_name":
                user["full_name"],

            "email":
                user["email"]
        }
    }
    

# ============================================================
# UPDATE PASSWORD
# ============================================================

@router.post("/update-password")
def update_password(request: UpdatePasswordRequest):

    student_id = request.student_id.strip().upper()
    current_password = request.current_password
    new_password = request.new_password

    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 6 characters."
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from your current password."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT student_id, password_hash
            FROM users
            WHERE student_id = ?
            """,
            (student_id,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Student account not found."
            )

        if not verify_password(
            current_password,
            user["password_hash"]
        ):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect."
            )

        new_password_hash = hash_password(new_password)

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE student_id = ?
            """,
            (new_password_hash, student_id)
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                status_code=404,
                detail="Student account not found."
            )

        connection.commit()

        return {
            "success": True,
            "message": "Password updated successfully."
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        print("UPDATE PASSWORD ERROR:")
        print(repr(error))
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to update password. Please try again later."
        )

    finally:
        connection.close()


# ============================================================
# UPDATE NAME
# ============================================================

@router.post("/update-name")
def update_name(request: UpdateNameRequest):
    student_id = request.student_id.strip().upper()
    current_password = request.current_password
    full_name = " ".join(request.full_name.strip().split())

    if not student_id:
        raise HTTPException(status_code=400, detail="Student ID is required.")

    if len(full_name) < 2 or len(full_name) > 100:
        raise HTTPException(
            status_code=400,
            detail="Name must contain between 2 and 100 characters."
        )

    if not current_password:
        raise HTTPException(status_code=400, detail="Current password is required.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT student_id, full_name, password_hash FROM users WHERE student_id = ?",
            (student_id,)
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="Student account not found.")

        if not verify_password(current_password, user["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect.")

        cursor.execute(
            "UPDATE users SET full_name = ? WHERE student_id = ?",
            (full_name, student_id)
        )

        if cursor.rowcount != 1:
            raise HTTPException(status_code=404, detail="Student account not found.")

        connection.commit()
        return {
            "success": True,
            "message": "Name updated successfully.",
            "student_id": student_id,
            "full_name": full_name
        }

    except HTTPException:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        print("UPDATE NAME ERROR:")
        print(repr(error))
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Unable to update name. Please try again later."
        )
    finally:
        connection.close()


# ============================================================
# PASSWORD RESET / EMAIL OTP
# ============================================================

OTP_EXPIRY_MINUTES = 10
RESET_TOKEN_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


def hash_reset_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def send_password_reset_email(email: str, otp: str):
    """Send the password-reset OTP through Resend's HTTPS API.

    Free/test setup:
    - Only RESEND_API_KEY is required.
    - When no sender is configured, Resend's testing sender
      ``onboarding@resend.dev`` is used automatically.
    - With that testing sender, Resend only allows delivery to the
      email address associated with the Resend account.

    Production setup:
    - After verifying a domain in Resend, set RESEND_FROM_EMAIL to an
      address on that verified domain.
    """

    resend_api_key = os.getenv("RESEND_API_KEY", "").strip()
    resend_from_email = os.getenv(
        "RESEND_FROM_EMAIL",
        "onboarding@resend.dev"
    ).strip()

    if not resend_api_key:
        raise RuntimeError(
            "RESEND_API_KEY is not configured in the deployment environment."
        )

    if not resend_from_email:
        resend_from_email = "onboarding@resend.dev"

    subject = "AcadAI Password Reset Code"
    text_body = f"""Hello,

We received a request to reset your AcadAI password.

Your 6-digit password reset code is:

{otp}

This code expires in {OTP_EXPIRY_MINUTES} minutes.

If you did not request this password reset, you can safely ignore this email.

Regards,
AcadAI
"""

    payload = {
        "from": resend_from_email,
        "to": [email],
        "subject": subject,
        "text": text_body,
    }

    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(
                    f"Resend returned HTTP {response.status}: {response_body}"
                )

    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Resend email API error (HTTP {error.code}): {error_body}"
        ) from error
    except URLError as error:
        raise RuntimeError(
            f"Unable to reach Resend email API: {error.reason}"
        ) from error


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest):
    email = str(request.email).strip().lower()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT student_id
            FROM users
            WHERE email = ?
            """,
            (email,)
        )
        user = cursor.fetchone()

        # Keep the response generic so account existence is not disclosed.
        if not user:
            return {
                "success": True,
                "message": "If an account exists for this email, a reset code has been sent."
            }

        # Invalidate previous reset codes for this account.
        cursor.execute(
            """
            UPDATE email_verifications
            SET used = TRUE,
                reset_token_hash = NULL,
                reset_token_expires_at = NULL
            WHERE student_id = ? AND used = FALSE
            """,
            (user["student_id"],)
        )

        otp = f"{secrets.randbelow(1_000_000):06d}"
        otp_hash = hash_reset_value(otp)
        now = datetime.now()
        expires_at = (now + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

        cursor.execute(
            """
            INSERT INTO email_verifications (
                student_id,
                email,
                otp_hash,
                expires_at,
                used,
                attempts,
                reset_token_hash,
                reset_token_expires_at,
                created_at
            )
            VALUES (?, ?, ?, ?, FALSE, 0, NULL, NULL, ?)
            """,
            (
                user["student_id"],
                email,
                otp_hash,
                expires_at,
                now.isoformat()
            )
        )
        connection.commit()

        try:
            send_password_reset_email(email, otp)
        except Exception as e:
            print("PASSWORD RESET EMAIL ERROR:")
            print(repr(e))
            traceback.print_exc()

            # Do not leave a usable reset code when email delivery fails.
            cursor.execute(
                """
                UPDATE email_verifications
                SET used = TRUE
                WHERE student_id = ? AND otp_hash = ?
                """,
                (user["student_id"], otp_hash)
            )
            connection.commit()

            raise HTTPException(
                status_code=500,
                detail="Unable to send password reset email. Please try again later."
            )

        return {
            "success": True,
            "message": "If an account exists for this email, a reset code has been sent."
        }

    except HTTPException:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        print("PASSWORD RESET PROCESS ERROR:")
        print(repr(error))
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Unable to process password reset request. Please try again later."
        )
    finally:
        connection.close()

@router.post("/verify-reset-code")
def verify_reset_code(request: VerifyResetCodeRequest):
    email = str(request.email).strip().lower()
    code = request.code.strip()

    if not re.fullmatch(r"\d{6}", code):
        raise HTTPException(
            status_code=400,
            detail="Reset code must contain exactly 6 digits."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                student_id,
                otp_hash,
                expires_at,
                used,
                attempts
            FROM email_verifications
            WHERE email = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email,)
        )
        verification = cursor.fetchone()

        if not verification or verification["used"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset code."
            )

        if verification["attempts"] >= MAX_OTP_ATTEMPTS:
            cursor.execute(
                """
                UPDATE email_verifications
                SET used = TRUE
                WHERE id = ?
                """,
                (verification["id"],)
            )
            connection.commit()
            raise HTTPException(
                status_code=400,
                detail="Too many incorrect attempts. Please request a new code."
            )

        try:
            expires_at = datetime.fromisoformat(verification["expires_at"])
        except (ValueError, TypeError):
            expires_at = datetime.min

        if datetime.now() > expires_at:
            cursor.execute(
                """
                UPDATE email_verifications
                SET used = TRUE
                WHERE id = ?
                """,
                (verification["id"],)
            )
            connection.commit()
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset code."
            )

        if not hmac.compare_digest(
            hash_reset_value(code),
            verification["otp_hash"]
        ):
            cursor.execute(
                """
                UPDATE email_verifications
                SET attempts = attempts + 1
                WHERE id = ?
                """,
                (verification["id"],)
            )
            connection.commit()
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset code."
            )

        reset_token = secrets.token_urlsafe(32)
        reset_token_hash = hash_reset_value(reset_token)
        reset_token_expires_at = (
            datetime.now() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
        ).isoformat()

        cursor.execute(
            """
            UPDATE email_verifications
            SET used = TRUE,
                reset_token_hash = ?,
                reset_token_expires_at = ?
            WHERE id = ?
            """,
            (
                reset_token_hash,
                reset_token_expires_at,
                verification["id"]
            )
        )
        connection.commit()

        return {
            "success": True,
            "message": "Reset code verified successfully.",
            "reset_token": reset_token
        }

    except HTTPException:
        raise
    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unable to verify reset code: {error}"
        )
    finally:
        connection.close()


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest):
    email = str(request.email).strip().lower()
    reset_token = request.reset_token.strip()
    new_password = request.new_password

    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters."
        )

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Reset token is required."
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        reset_token_hash = hash_reset_value(reset_token)

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                reset_token_expires_at
            FROM email_verifications
            WHERE email = ?
              AND reset_token_hash = ?
              AND used = TRUE
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email, reset_token_hash)
        )
        verification = cursor.fetchone()

        if not verification:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset session."
            )

        try:
            token_expires_at = datetime.fromisoformat(
                verification["reset_token_expires_at"]
            )
        except (ValueError, TypeError):
            token_expires_at = datetime.min

        if datetime.now() > token_expires_at:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset session."
            )

        new_password_hash = hash_password(new_password)

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE student_id = ? AND email = ?
            """,
            (
                new_password_hash,
                verification["student_id"],
                email
            )
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                status_code=404,
                detail="Student account not found."
            )

        cursor.execute(
            """
            UPDATE email_verifications
            SET reset_token_hash = NULL,
                reset_token_expires_at = NULL
            WHERE id = ?
            """,
            (verification["id"],)
        )

        connection.commit()

        return {
            "success": True,
            "message": "Password reset successfully. You can now log in."
        }

    except HTTPException:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unable to reset password: {error}"
        )
    finally:
        connection.close()


# ============================================================
# GET PROFILE
# ============================================================

@router.get("/profile/{student_id}")
def get_profile(student_id: str):

    student_id = (
        student_id
        .strip()
        .upper()
    )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            student_id,
            full_name,
            email,
            profile_picture
        FROM users
        WHERE student_id = ?
        """,
        (student_id,)
    )

    user = cursor.fetchone()

    connection.close()


    if not user:

        raise HTTPException(
            status_code=404,
            detail="Student account not found."
        )


    profile_picture = None

    if user["profile_picture"]:
        stored_picture = str(user["profile_picture"]).strip()

        # New profile pictures are stored as permanent Cloudinary URLs.
        if stored_picture.startswith(("http://", "https://")):
            profile_picture = stored_picture
        else:
            # Backward compatibility for old pictures that were stored
            # on the Render filesystem.
            profile_picture = (
                "/uploads/profile_pictures/"
                + stored_picture
            )


    return {
        "student_id":
            user["student_id"],

        "full_name":
            user["full_name"],

        "email":
            user["email"],

        "profile_picture":
            profile_picture
    }


# ============================================================
# UPLOAD PROFILE PICTURE
# ============================================================

@router.post("/profile-picture/{student_id}")
async def upload_profile_picture(
    student_id: str,
    file: UploadFile = File(...)
):

    student_id = (
        student_id
        .strip()
        .upper()
    )


    # --------------------------------------------------------
    # VALIDATE FILE TYPE
    # --------------------------------------------------------

    if file.content_type not in ALLOWED_IMAGE_TYPES:

        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP images are allowed."
        )


    # --------------------------------------------------------
    # READ FILE
    # --------------------------------------------------------

    image_data = await file.read()


    # --------------------------------------------------------
    # VALIDATE FILE SIZE
    # --------------------------------------------------------

    if len(image_data) > MAX_PROFILE_SIZE:

        raise HTTPException(
            status_code=400,
            detail="Profile picture must be smaller than 5 MB."
        )


    if len(image_data) == 0:

        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty."
        )


    # --------------------------------------------------------
    # CHECK STUDENT
    # --------------------------------------------------------

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            profile_picture
        FROM users
        WHERE student_id = ?
        """,
        (student_id,)
    )

    user = cursor.fetchone()


    if not user:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Student account not found."
        )


    # --------------------------------------------------------
    # GET OLD PICTURE
    # --------------------------------------------------------

    old_picture = user["profile_picture"]

    # --------------------------------------------------------
    # UPLOAD NEW PICTURE TO CLOUDINARY
    # --------------------------------------------------------

    try:
        _configure_cloudinary()

        cloudinary_result = cloudinary.uploader.upload(
            io.BytesIO(image_data),
            resource_type="image",
            public_id=_cloudinary_public_id(student_id),
            overwrite=True,
            invalidate=True,
        )

        profile_picture_url = cloudinary_result.get("secure_url")

        if not profile_picture_url:
            raise RuntimeError(
                "Cloudinary upload succeeded but did not return a secure URL."
            )

    except Exception as error:
        connection.close()
        print("CLOUDINARY PROFILE PICTURE UPLOAD ERROR:")
        print(repr(error))
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to upload profile picture. Please try again later."
        )

    # --------------------------------------------------------
    # SAVE CLOUDINARY URL IN DATABASE
    # --------------------------------------------------------

    try:
        cursor.execute(
            """
            UPDATE users
            SET profile_picture = ?
            WHERE student_id = ?
            """,
            (
                profile_picture_url,
                student_id
            )
        )

        if cursor.rowcount != 1:
            raise RuntimeError("Student account could not be updated.")

        connection.commit()

    except Exception as error:
        connection.rollback()
        connection.close()

        # The Cloudinary upload succeeded but the database update failed.
        # Remove the new image so we don't leave an orphaned cloud asset.
        _delete_cloudinary_picture(student_id)

        print("PROFILE PICTURE DATABASE UPDATE ERROR:")
        print(repr(error))
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to save profile picture. Please try again later."
        )

    connection.close()

    # --------------------------------------------------------
    # CLEAN UP OLD LOCAL PICTURE, IF THIS USER HAD ONE
    # --------------------------------------------------------

    # Old versions of the application stored only a filename in the
    # database and saved the actual file under data/profile_pictures.
    # Keep this cleanup for backward compatibility.
    if old_picture:
        old_picture_value = str(old_picture).strip()

        if not old_picture_value.startswith(("http://", "https://")):
            old_path = PROFILE_DIR / old_picture_value

            try:
                if old_path.exists() and old_path.is_file():
                    old_path.unlink()
            except OSError:
                print(
                    f"Unable to remove old local profile picture: {old_path}"
                )

    return {
        "success": True,
        "message": "Profile picture updated successfully.",
        "profile_picture": profile_picture_url
    }

# ============================================================
# DELETE ACCOUNT
# ============================================================

@router.delete("/account/{student_id}")
def delete_account(student_id: str):

    student_id = (
        student_id
        .strip()
        .upper()
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # ----------------------------------------------------
        # CHECK ACCOUNT AND GET PROFILE PICTURE
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                profile_picture
            FROM users
            WHERE student_id = ?
            """,
            (student_id,)
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Student account not found."
            )

        old_picture = user["profile_picture"]

        # ----------------------------------------------------
        # DELETE USER-OWNED DATA
        #
        # academic_profiles, academic_subjects and
        # academic_semesters already use ON DELETE CASCADE
        # through users(student_id).
        #
        # notifications, feedback and email_verifications
        # are explicitly deleted here for a complete cleanup.
        # ----------------------------------------------------

        # Notifications
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'notifications'
            ) AS table_exists
            """
        )

        notifications_table = cursor.fetchone()

        if notifications_table and notifications_table["table_exists"]:
            cursor.execute(
                """
                DELETE FROM notifications
                WHERE student_id = ?
                """,
                (student_id,)
            )

        # Feedback
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'feedback'
            ) AS table_exists
            """
        )

        feedback_table = cursor.fetchone()

        if feedback_table and feedback_table["table_exists"]:
            cursor.execute(
                """
                DELETE FROM feedback
                WHERE student_id = ?
                """,
                (student_id,)
            )

        # Email verification
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'email_verifications'
            ) AS table_exists
            """
        )

        email_verifications_table = cursor.fetchone()

        if email_verifications_table and email_verifications_table["table_exists"]:
            cursor.execute(
                """
                DELETE FROM email_verifications
                WHERE student_id = ?
                """,
                (student_id,)
            )

        # ----------------------------------------------------
        # DELETE USER
        #
        # This automatically removes:
        #   - academic_profiles
        #   - academic_subjects
        #   - academic_semesters
        #
        # because their foreign keys use ON DELETE CASCADE.
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM users
            WHERE student_id = ?
            """,
            (student_id,)
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                status_code=404,
                detail="Student account not found."
            )

        # ----------------------------------------------------
        # COMMIT DATABASE CLEANUP FIRST
        # ----------------------------------------------------

        connection.commit()

        # ----------------------------------------------------
        # DELETE PROFILE PICTURE
        #
        # New pictures are stored on Cloudinary. Older accounts
        # may still contain a local filename, so support both.
        # ----------------------------------------------------

        profile_picture_deleted = True

        if old_picture:
            old_picture_value = str(old_picture).strip()

            if old_picture_value.startswith(("http://", "https://")):
                # New Cloudinary-backed picture.
                profile_picture_deleted = _delete_cloudinary_picture(
                    student_id
                )

            else:
                # Backward compatibility for old Render-local pictures.
                old_path = PROFILE_DIR / old_picture_value

                try:
                    if old_path.exists() and old_path.is_file():
                        old_path.unlink()
                except OSError:
                    profile_picture_deleted = False

        return {
            "success": True,
            "message": "Account and all associated data deleted successfully.",
            "student_id": student_id,
            "profile_picture_deleted": profile_picture_deleted
        }

    except HTTPException:

        connection.rollback()
        raise

    except Exception as error:

        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Unable to delete account: {error}"
        )

    finally:

        connection.close()
