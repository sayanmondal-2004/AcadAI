/* ==========================================
   AcadAI Advisor - Shared Authentication
   ========================================== */

const API_URL = "https://acad-ai-backend-6494.onrender.com";

const STUDENT_ID = localStorage.getItem("student_id");

const DEFAULT_AVATAR =
    "https://ui-avatars.com/api/?name=Student&background=e0e7ff&color=4f46e5&size=128";

// ==========================================
// REQUIRE LOGIN
// ==========================================

function requireLogin() {
    if (!STUDENT_ID) {
        window.location.href = "login.html";
        return false;
    }

    return true;
}

// ==========================================
// DEFAULT PROFILE PICTURE
// ==========================================

function setDefaultProfilePicture() {
    document.querySelectorAll(".student-profile-image").forEach(
        function (image) {
            image.src = DEFAULT_AVATAR;
        }
    );
}

// ==========================================
// LOAD STUDENT PROFILE
// ==========================================

async function loadStudentProfile() {
    if (!STUDENT_ID) return;

    try {
        const response = await fetch(
            `${API_URL}/auth/profile/${encodeURIComponent(STUDENT_ID)}`
        );

        if (!response.ok) {
            console.error("Unable to load profile:", response.status);
            return;
        }

        const profile = await response.json();

        // Support APIs that return either a direct profile
        // or a profile object nested inside another object.
        const studentProfile = profile.profile || profile;

        // ------------------------------------------
        // PROFILE PICTURE
        // ------------------------------------------

        const picture =
            studentProfile.profile_picture ||
            studentProfile.profilePicture ||
            studentProfile.avatar_url ||
            studentProfile.avatar;

        document.querySelectorAll(".student-profile-image").forEach(
            function (image) {
                image.onerror = function () {
                    this.onerror = null;
                    this.src = DEFAULT_AVATAR;
                };

                if (picture) {
                    const pictureUrl = String(picture).trim();

                    if (
                        pictureUrl.startsWith("https://") ||
                        pictureUrl.startsWith("http://")
                    ) {
                        // Cloudinary URL or another absolute image URL.
                        image.src = pictureUrl;
                    } else {
                        // Backward compatibility for relative image paths.
                        image.src =
                            API_URL +
                            (pictureUrl.startsWith("/")
                                ? pictureUrl
                                : "/" + pictureUrl);
                    }
                } else {
                    image.src = DEFAULT_AVATAR;
                }
            }
        );

        // ------------------------------------------
        // STUDENT NAME
        // ------------------------------------------

        const nameCandidates = [
            studentProfile.full_name,
            studentProfile.name,
            studentProfile.student_name,
            studentProfile.username,
            profile.full_name,
            profile.name
        ];

        const studentName = nameCandidates.find(function (value) {
            return (
                typeof value === "string" &&
                value.trim() !== "" &&
                value.trim().toLowerCase() !== "student"
            );
        });

        if (studentName) {
            const cleanName = studentName.trim();

            // Update all supported name locations.
            document.querySelectorAll(
                ".student-name, #sidebar-student-name, #mobile-menu-student-name"
            ).forEach(function (element) {
                element.textContent = cleanName;
            });

            // Keep the name available to other frontend pages.
            localStorage.setItem("student_name", cleanName);

            try {
                const cachedProfile = JSON.parse(
                    localStorage.getItem("student_profile") || "{}"
                );

                cachedProfile.name = cleanName;
                cachedProfile.full_name = cleanName;

                localStorage.setItem(
                    "student_profile",
                    JSON.stringify(cachedProfile)
                );
            } catch (error) {
                console.warn("Could not cache student name:", error);
            }
        }

        // ------------------------------------------
        // STUDENT ID
        // ------------------------------------------

        const studentId =
            studentProfile.student_id || STUDENT_ID;

        document.querySelectorAll(
            ".student-id, #student-id"
        ).forEach(function (element) {
            if (studentId) {
                element.textContent = studentId;
            }
        });

        // ------------------------------------------
        // EMAIL
        // ------------------------------------------

        document.querySelectorAll(".student-email").forEach(
            function (element) {
                if (studentProfile.email) {
                    element.textContent = studentProfile.email;
                }
            }
        );

        // ------------------------------------------
        // DEPARTMENT
        // ------------------------------------------

        document.querySelectorAll(".student-department").forEach(
            function (element) {
                if (studentProfile.department) {
                    element.textContent = studentProfile.department;
                }
            }
        );

        // ------------------------------------------
        // YEAR
        // ------------------------------------------

        document.querySelectorAll(".student-year").forEach(
            function (element) {
                if (studentProfile.year) {
                    element.textContent = studentProfile.year;
                }
            }
        );

    } catch (error) {
        console.error("Unable to load student profile:", error);
    }
}

// ==========================================
// LOGOUT
// ==========================================

function logout() {
    localStorage.removeItem("student_id");
    localStorage.removeItem("student_profile");
    localStorage.removeItem("student_name");
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");

    window.location.href = "login.html";
}

// ==========================================
// DELETE ACCOUNT
// ==========================================

async function deleteAccount() {
    if (!STUDENT_ID) {
        alert("No logged-in student found.");
        return;
    }

    const confirmed = confirm(
        "Are you sure you want to permanently delete your account? This action cannot be undone."
    );

    if (!confirmed) return;

    try {
        const response = await fetch(
            `${API_URL}/auth/delete-account/${encodeURIComponent(STUDENT_ID)}`,
            {
                method: "DELETE"
            }
        );

        let data = {};

        try {
            data = await response.json();
        } catch (_) {
            // The server may return an empty response.
        }

        if (!response.ok) {
            throw new Error(
                data.detail || "Unable to delete account."
            );
        }

        localStorage.removeItem("student_id");
        localStorage.removeItem("student_profile");
        localStorage.removeItem("student_name");
        localStorage.removeItem("token");
        localStorage.removeItem("access_token");

        alert("Your account has been deleted successfully.");
        window.location.href = "login.html";

    } catch (error) {
        console.error("Account deletion error:", error);

        alert(error.message || "Unable to delete account.");
    }
}

// ==========================================
// INITIALIZE
// ==========================================

document.addEventListener("DOMContentLoaded", function () {
    loadStudentProfile();
});