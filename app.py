import requests
import jwt
import streamlit as st
from urllib.parse import urlparse, parse_qs
from http.cookies import SimpleCookie
import os
import pandas as pd

# Function to check if user is logged in
def check_session_and_redirect():
    # Check if user is logged in
    if "user" not in st.session_state:
        # Add a button to navigate to the login page
        if st.button("Login"):
            login_url = "https://kor-keep2.seagate.com:54345/auth/http://10.7.194.231:8501"
            st.write("Redirecting to the login page...")
            st.markdown(f"<meta http-equiv='refresh' content='0; url={login_url}'>", unsafe_allow_html=True)
        #st.warning("User not logged in. Redirecting to login page...")

        # Redirect to the provided login link
        #login_url = "https://kor-keep2.seagate.com:54345/auth/http://10.7.194.231:8501"
        #st.markdown(f"[Click here to log in]({login_url})")
        # Parse the redirect link after login
    else:
        if st.button("Logout"):
            st.session_state.pop("user")
            st.success("Logged out successfully. Please refresh the page.")

# Function to get the current URL, parse it, and save session data
def get_current_url_and_save_session():
    # Get the current URL parameters
    #current_url_params = st.experimental_get_query_params()
    #st.write(current_url_params)
    current_url_params = st.query_params
    # st.write(params)
    # Extract the JWT token from the 'ref' parameter
    jwt_token = current_url_params.get("ref", None)
    if jwt_token:
        #st.write("JWT Token:", jwt_token)

        # Decode the JWT token
        try:
            decoded_token = jwt.decode(jwt_token, options={"verify_signature": False})
            #st.write("Decoded JWT Token:")
            #st.json(decoded_token)

            # Save decoded token to session state
            st.session_state["user"] = decoded_token

            # Save gid to session state if present
            gid = decoded_token.get("gid")
            # Remove 'ref' parameter from the URL after processing
            # st.query_params.clear()
            # for k, v in current_url_params.items():
            #     if k != "ref":
            #         st.query_params[k] = v
            if gid:
                st.session_state["gid"] = gid
                #st.success(f"GID saved to session state: {gid}")
        except jwt.PyJWTError as e:
            st.error(f"Error decoding JWT token: {e}")
    else:
        pass
        
# Function to print a welcome message to the user with enhanced visuals
def print_welcome_message():
    if "user" in st.session_state:
        user = st.session_state["user"]
        full_name = user.get("fullname", "User")
        st.markdown(
            f"""
            <div style="text-align: center; padding: 20px; background-color: #f0f8ff; border-radius: 10px;">
                <h1 style="color: #4CAF50;">🌟 Welcome, {full_name}! 🌟</h1>
                <p style="font-size: 18px; color: #555;">We're glad to have you here. Let's make today productive! 🚀</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="text-align: center; padding: 20px; background-color: #f0f8ff; border-radius: 10px;">
                <h1 style="color: #4CAF50;">🌟 Welcome, Guest! 🌟</h1>
                <p style="font-size: 18px; color: #555;">Please log in to access more features. 🔒</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# Save session_state["user"] to a cookie
def save_user_to_cookie():
    if "user" in st.session_state:
        user_data = st.session_state["user"]
        cookie = SimpleCookie()
        cookie["user"] = str(user_data)
        cookie["user"]["path"] = "/"
        st.markdown(
            f"<script>document.cookie = '{cookie.output(header='', sep='; ')}';</script>",
            unsafe_allow_html=True
        )

# Load cookie data into session_state["user"]
def load_user_from_cookie():
    cookie_str = os.environ.get("HTTP_COOKIE", "")
    if cookie_str:
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        if "user" in cookie:
            user_data = cookie["user"].value
            st.session_state["user"] = eval(user_data)  # Convert string back to dictionary
            st.write("User data loaded from cookie.")

# Function to check user access based on user_access_control_list.csv
def check_user_access(page_name):
    if "user" in st.session_state:
        user_gid = st.session_state["user"].get("gid")
        if user_gid:
            # Load the access control list
            acl = pd.read_csv("MASTER/user_access_control_list.csv")
            # Check if the user has access to the specified page
            user_access = acl[(acl["GID"] == int(user_gid)) & ((acl["Page"] == page_name) | (acl["Page"] == "All"))]
            if user_access.empty:
                st.error("You do not have access to this page.")
                st.stop()
            else:
                st.success("Access granted.")

# Example usage

# Call the function to load user data from a cookie
load_user_from_cookie()

#get_current_url_and_save_session()
get_current_url_and_save_session()
check_session_and_redirect()
print_welcome_message()

# Call the function to save user data to a cookie
save_user_to_cookie()

# Example usage
page_name = os.path.basename(__file__).replace(".py", "")
check_user_access(page_name)

st.markdown("""
<style>



/* Hide 4th page in sidebar nav */
[data-testid="stSidebarNav"] ul li:nth-of-type(4) {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)