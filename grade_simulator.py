import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime

st.set_page_config(
    page_title="CGPA Calculator",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def init_db():
    conn = sqlite3.connect('cgpa_data.db', check_same_thread=False)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_code TEXT NOT NULL,
            credit INTEGER NOT NULL,
            grade REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    return conn

conn = init_db()

def hash_password(password):
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt + key

def verify_password(stored_password, provided_password):
    salt = stored_password[:32]
    stored_key = stored_password[32:]
    key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
    return key == stored_key

def create_user(username, full_name, password):
    try:
        c = conn.cursor()
        hashed_password = hash_password(password)
        c.execute(
            "INSERT INTO users (username, full_name, password) VALUES (?, ?, ?)",
            (username, full_name, hashed_password)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False 
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False

def verify_user(username, password):
    try:
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        
        if user:
            user_id, stored_password = user
            if verify_password(stored_password, password):
                return user_id
        return None
    except Exception as e:
        st.error(f"Error verifying user: {e}")
        return None

def get_user_data(user_id):
    try:
        c = conn.cursor()
        c.execute("SELECT username, full_name FROM users WHERE id = ?", (user_id,))
        user_info = c.fetchone()
        
        if not user_info:
            return None
            
        username, full_name = user_info
        
        c.execute(
            "SELECT id, course_code, credit, grade FROM courses WHERE user_id = ? ORDER BY created_at",
            (user_id,)
        )
        courses = [
            {"id": row[0], "code": row[1], "credit": row[2], "grade": row[3]}
            for row in c.fetchall()
        ]
        
        return {
            "username": username,
            "full_name": full_name,
            "courses": courses
        }
    except Exception as e:
        st.error(f"Error fetching user data: {e}")
        return None

def save_course(user_id, course_code, credit, grade):
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO courses (user_id, course_code, credit, grade) VALUES (?, ?, ?, ?)",
            (user_id, course_code, credit, grade)
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error saving course: {e}")
        return False

def update_course(user_id, course_id, course_code, credit, grade):
    try:
        c = conn.cursor()
        c.execute(
            "UPDATE courses SET course_code = ?, credit = ?, grade = ? WHERE id = ? AND user_id = ?",
            (course_code, credit, grade, course_id, user_id)
        )
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        st.error(f"Error updating course: {e}")
        return False

def delete_course(user_id, course_id):
    try:
        c = conn.cursor()
        c.execute(
            "DELETE FROM courses WHERE id = ? AND user_id = ?",
            (course_id, user_id)
        )
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        st.error(f"Error deleting course: {e}")
        return False

def delete_user_account(user_id):
    try:
        c = conn.cursor()
        c.execute("DELETE FROM courses WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting account: {e}")
        return False

def get_all_users():
    try:
        c = conn.cursor()
        c.execute("SELECT id, username, full_name FROM users ORDER BY username")
        return [
            {"id": row[0], "username": row[1], "full_name": row[2]}
            for row in c.fetchall()
        ]
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []

def calculate_cgpa(courses):
    if not courses:
        return 0, 0, 0
    
    total_points = sum(course["credit"] * course["grade"] for course in courses)
    total_credits = sum(course["credit"] for course in courses)
    
    if total_credits == 0:
        return 0, 0, 0
    
    cgpa = total_points / total_credits
    return total_points, total_credits, cgpa

def initialize_session_state():
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_data" not in st.session_state:
        st.session_state.user_data = None
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "login_attempted" not in st.session_state:
        st.session_state.login_attempted = False

def home_page():
    st.title("CGPA Calculator")
    st.write("Welcome to the CGPA Calculator app! Track your academic performance securely.")
    
    if st.button("Let's Start", type="primary", use_container_width=True):
        st.session_state.page = "signup"
        st.rerun()
    
    st.subheader("Existing Users - Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        submitted = st.form_submit_button("Login")
        
        if submitted:
            user_id = verify_user(username, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.user_data = get_user_data(user_id)
                st.session_state.page = "dashboard"
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def signup_page():
    st.title("Create Your Profile")
    
    with st.form("signup_form"):
        full_name = st.text_input("Full Name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        submitted = st.form_submit_button("Create Profile")
        
        if submitted:
            if not full_name or not username or not password:
                st.error("Please fill in all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters long")
            elif any(c in username for c in " /\\:<>|?*\"'"):
                st.error("Username cannot contain special characters")
            else:
                if create_user(username, full_name, password):
                    st.success("Profile created successfully! Please login.")
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("Username already exists. Please choose a different one.")
    
    if st.button("Back to Home"):
        st.session_state.page = "home"
        st.rerun()

def dashboard_page():
    user_data = st.session_state.user_data
    
    st.title(f"Welcome, {user_data['full_name']}!")
    st.subheader("CGPA Dashboard")
    
    total_points, total_credits, cgpa = calculate_cgpa(user_data["courses"])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Points", f"{total_points:.2f}")
    col2.metric("Total Credits", total_credits)
    col3.metric("CGPA", f"{cgpa:.2f}")
    
    st.subheader("Add New Course")
    with st.form("add_course_form"):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            course_code = st.text_input("Course Code")
        with col2:
            credit = st.selectbox("Credit", [1, 2, 3, 4, 4.5])
        with col3:
            grade_options  =  [4.00, 3.75, 3.70, 3.50, 3.30, 3.25, 3.00, 2.75, 2.70, 2.50, 2.30, 2.25, 2.00, 1.70, 1.30, 1.00, 0.00]
            grade = st.selectbox("Grade", grade_options, format_func=lambda x: f"{x:.2f}")
        
        submitted = st.form_submit_button("Add Course")
        
        if submitted:
            if not course_code:
                st.error("Please enter a course code")
            else:
                if save_course(st.session_state.user_id, course_code, credit, grade):
                    st.session_state.user_data = get_user_data(st.session_state.user_id)
                    st.success("Course added successfully!")
                    st.rerun()
                else:
                    st.error("Error adding course")
    
    if user_data["courses"]:
        st.subheader("Your Courses")
        
        for i, course in enumerate(user_data["courses"]):
            with st.expander(f"{course['code']} - Credit: {course['credit']}, Grade: {course['grade']:.2f}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    new_code = st.text_input("Course Code", value=course["code"], 
                                           key=f"edit_code_{i}_{course['id']}")
                with col2:
                    new_credit = st.selectbox("Credit", [1, 2, 3, 4, 4.5], 
                                            index=[1, 2, 3, 4, 4.5].index(course["credit"]),
                                            key=f"edit_credit_{i}_{course['id']}")
                with col3:
                    grade_labels = [f"{g:.2f}" for g in grade_options] 

                    grade_index = grade_options.index(course["grade"])

                    new_grade_label = st.selectbox(
                        "Grade",
                        grade_labels,
                        index=grade_index,
                        key=f"edit_grade_{i}_{course['id']}"
                    )
                    new_grade = float(new_grade_label)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Update", key=f"update_{i}_{course['id']}"):
                        if update_course(st.session_state.user_id, course["id"], new_code, new_credit, new_grade):
                            st.session_state.user_data = get_user_data(st.session_state.user_id)
                            st.success("Course updated successfully!")
                            st.rerun()
                        else:
                            st.error("Error updating course")
                with col2:
                    if st.button("Delete", key=f"delete_{i}_{course['id']}"):
                        if delete_course(st.session_state.user_id, course["id"]):
                            st.session_state.user_data = get_user_data(st.session_state.user_id)
                            st.success("Course deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Error deleting course")
    else:
        st.info("No courses added yet. Add your first course above!")
    
    st.subheader("Account Management")
    if st.button("Delete Account", type="secondary"):
        if st.checkbox("I understand that this will permanently delete all my data"):
            if st.button("Confirm Delete Account", type="primary"):
                if delete_user_account(st.session_state.user_id):
                    st.success("Account deleted successfully!")
                    st.session_state.user_id = None
                    st.session_state.user_data = None
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("Error deleting account")
    
    if st.button("Logout"):
        st.session_state.user_id = None
        st.session_state.user_data = None
        st.session_state.page = "home"
        st.rerun()

def main():
    initialize_session_state()
    
    if st.session_state.page == "home":
        home_page()
    elif st.session_state.page == "signup":
        signup_page()
    elif st.session_state.page == "dashboard":
        dashboard_page()

if __name__ == "__main__":

    main()
