import jwt
import os
import pandas as pd
import streamlit as st

from streamlit_cookies_manager import EncryptedCookieManager


# ==================================================
# COOKIE MANAGER
# ==================================================

cookies = EncryptedCookieManager(
    prefix="testtime_app",
    password="my_super_secret_key_2026"
)

if not cookies.ready():
    st.stop()


# ==================================================
# COOKIE FUNCTIONS
# ==================================================

def save_user_to_cookie():

    if "user" not in st.session_state:
        return

    user = st.session_state["user"]

    cookies["gid"] = str(
        user.get("gid", "")
    )

    cookies["fullname"] = str(
        user.get("fullname", "")
    )

    cookies["email"] = str(
        user.get("mail", "")
    )

    cookies.save()


def load_user_from_cookie():

    if "user" in st.session_state:
        return

    gid = cookies.get("gid")

    if not gid:
        return

    st.session_state["user"] = {
        "gid": gid,
        "fullname": cookies.get(
            "fullname",
            ""
        ),
        "mail": cookies.get(
            "email",
            ""
        )
    }

    st.session_state["gid"] = gid


def clear_user_cookie():

    keys = [
        "gid",
        "fullname",
        "email"
    ]

    for key in keys:

        if key in cookies:
            del cookies[key]

    cookies.save()


# ==================================================
# AUTH
# ==================================================

def get_current_url_and_save_session():

    current_url_params = st.query_params

    jwt_token = current_url_params.get(
        "ref",
        None
    )

    if not jwt_token:
        return

    try:

        decoded_token = jwt.decode(
            jwt_token,
            options={
                "verify_signature": False
            }
        )

        st.session_state["user"] = decoded_token

        gid = decoded_token.get("gid")

        if gid:
            st.session_state["gid"] = gid

        save_user_to_cookie()

    except jwt.PyJWTError as ex:

        st.error(
            f"JWT Decode Error : {ex}"
        )


def logout():

    clear_user_cookie()

    st.session_state.clear()

    st.rerun()


def check_session_and_redirect():

    if "user" not in st.session_state:

        st.warning(
            "User not logged in"
        )

        if st.button("Login"):

            login_url = (
                "https://kor-keep2.seagate.com:54345/auth/"
                "http://10.7.194.231:8501"
            )

            st.markdown(
                f"""
                <meta
                  http-equiv='refresh'
                  content='0; url={login_url}'>
                """,
                unsafe_allow_html=True
            )




# ==================================================
# UI
# ==================================================

def print_welcome_message():

    if "user" not in st.session_state:

        st.info(
            "Please login"
        )

        return
    col1, col2 = st.columns([10,1])

    with col1:
        user = st.session_state["user"]

        st.success(
            f"Welcome "
            f"{user.get('fullname','User')}"
        )
    with col2:

        if st.button("Logout"):

            logout()





# ==================================================
# ACL
# ==================================================

def check_user_access(page_name):

    if "user" not in st.session_state:
        return

    user_gid = st.session_state[
        "user"
    ].get(
        "gid"
    )

    if not user_gid:
        return

    try:

        acl = pd.read_csv(
            "MASTER/user_access_control_list.csv"
        )

        user_access = acl[
            (
                acl["GID"]
                ==
                int(user_gid)
            )
            &
            (
                (acl["Page"] == page_name)
                |
                (acl["Page"] == "All")
            )
        ]

        if user_access.empty:

            st.error(
                "You do not have access "
                "to this page."
            )

            st.stop()

    except Exception as ex:

        st.error(
            f"ACL Error : {ex}"
        )


# ==================================================
# REQUIRE LOGIN
# ==================================================

def init_auth():

    load_user_from_cookie()

    get_current_url_and_save_session()

    check_session_and_redirect()