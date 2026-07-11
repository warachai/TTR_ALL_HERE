import os
from dataclasses import dataclass
import config
from typing import Optional, List

import pandas as pd


@dataclass
class User:
    user_id: str
    api_key: str = ""
    role: str = "user"
    model: str = "gpt-4o"
    active: bool = True


class UserManager:

    DEFAULT_COLUMNS = [
        "user_id",
        "api_key",
        "role",
        "model",
        "active"
    ]

    def __init__(self, csv_path=config.USER_FILE_NAME):
        self.csv_path = csv_path
        self._initialize()

    def _initialize(self):

        directory = os.path.dirname(self.csv_path)

        if directory:
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(self.csv_path):

            pd.DataFrame(
                columns=self.DEFAULT_COLUMNS
            ).to_csv(
                self.csv_path,
                index=False
            )

    def _load(self) -> pd.DataFrame:

        return pd.read_csv(self.csv_path)

    def _save(self, df: pd.DataFrame):

        df.to_csv(
            self.csv_path,
            index=False
        )

    # ==================================================
    # User Functions
    # ==================================================

    def save_user(self, user: User):

        df = self._load()

        mask = df["user_id"] == str(user.user_id)

        if mask.any():

            df.loc[
                mask,
                ["api_key", "role", "model", "active"]
            ] = [
                user.api_key,
                user.role,
                user.model,
                user.active
            ]

        else:

            df.loc[len(df)] = [
                user.user_id,
                user.api_key,
                user.role,
                user.model,
                user.active
            ]

        self._save(df)

    def get_user(self, user_id: str) -> Optional[User]:

        df = self._load()

        result = df[
            df["user_id"] == str(user_id)
        ]

        #print(df.head()) 

        #print("MMM df result:", len(result), "user_id:", user_id)

        if result.empty:
            return None

        row = result.iloc[0]

        return User(
            user_id=row["user_id"],
            api_key=row["api_key"],
            role=row["role"],
            model=row["model"],
            active=bool(row["active"])
        )

    def delete_user(self, user_id: str):

        df = self._load()

        df = df[
            df["user_id"] != user_id
        ]

        self._save(df)

    def get_all_users(self) -> List[User]:

        df = self._load()

        users = []

        for _, row in df.iterrows():

            users.append(
                User(
                    user_id=row["user_id"],
                    api_key=row["api_key"],
                    role=row["role"],
                    model=row["model"],
                    active=bool(row["active"])
                )
            )

        return users

    # ==================================================
    # API Key Functions
    # ==================================================

    def get_api_key(self, user_id: str) -> Optional[str]:

        user = self.get_user(user_id)

        return None if user is None else user.api_key

    def set_api_key(self, user_id: str, api_key: str):

        user = self.get_user(user_id)

        if user is None:

            user = User(
                user_id=user_id,
                api_key=api_key
            )

        else:

            user.api_key = api_key

        self.save_user(user)

    # ==================================================
    # Utility
    # ==================================================

    def user_exists(self, user_id: str) -> bool:

        return self.get_user(user_id) is not None

    def get_dataframe(self) -> pd.DataFrame:

        return self._load()

    def reset(self):

        pd.DataFrame(
            columns=self.DEFAULT_COLUMNS
        ).to_csv(
            self.csv_path,
            index=False
        )