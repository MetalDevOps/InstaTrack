# profile_username = "__gabriel__vp__"

import instaloader.instaloader as instaloader
import os
import time
import sqlite3
import argparse
from datetime import datetime
from instaloader.exceptions import ConnectionException, TooManyRequestsException

# Create an instance of Instaloader
L = instaloader.Instaloader()

# Login with credentials from environment variables
username = os.getenv("INSTA_USERNAME")
password = os.getenv("INSTA_PASSWORD")

# Perform login
L.login(username, password)

# Initialize SQLite database
conn = sqlite3.connect("instagram_data.db")
cursor = conn.cursor()


def fetch_users_with_retry(user_getter, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            return list(user_getter())
        except (ConnectionException, TooManyRequestsException) as e:
            print(f"Rate limit hit or connection error: {e}. Retrying in 60 seconds...")
            time.sleep(60)  # Wait for 60 seconds before retrying
            retries += 1
    raise Exception("Max retries reached. Unable to fetch users.")


def save_users_to_db(usernames, table_name, date_column):
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for username in usernames:
        try:
            cursor.execute(
                f"INSERT OR IGNORE INTO {table_name} (username, {date_column}) VALUES (?, ?)",
                (username, current_date),
            )
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
    conn.commit()


def ensure_table_structure(profile_username):
    followers_table = f"Followers_{profile_username}"
    following_table = f"Following_{profile_username}"

    # Ensure followers table structure
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {followers_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            date_followed TEXT,
            date_followed_back TEXT
        )
    """
    )

    # Ensure following table structure
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {following_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            date_followed TEXT,
            date_followed_back TEXT
        )
    """
    )

    conn.commit()
    return followers_table, following_table


def fetch_and_save_data(profile_username):
    followers_table, following_table = ensure_table_structure(profile_username)

    # Fetch current followers and followings
    profile = instaloader.Profile.from_username(L.context, profile_username)
    current_followers = fetch_users_with_retry(profile.get_followers)
    current_followings = fetch_users_with_retry(profile.get_followees)

    # Save current followers and followings to the respective tables
    save_users_to_db(
        [follower.username for follower in current_followers],
        followers_table,
        "date_followed",
    )
    save_users_to_db(
        [following.username for following in current_followings],
        following_table,
        "date_followed",
    )

    print(
        f"Followers and following lists for {profile_username} have been updated in the database."
    )


def check_follow_me_back(profile_username):
    followers_table, following_table = ensure_table_structure(profile_username)

    cursor.execute(f"SELECT username FROM {following_table}")
    followings = [row[0] for row in cursor.fetchall()]

    cursor.execute(f"SELECT username FROM {followers_table}")
    followers = [row[0] for row in cursor.fetchall()]

    not_following_back = [user for user in followings if user not in followers]

    print(f"\nUsers you follow who are not following you back:")
    for user in not_following_back:
        print(user)


def main():
    parser = argparse.ArgumentParser(description="Instagram Follower/Following Tracker")
    parser.add_argument(
        "profile_username", type=str, help="Instagram profile username to track"
    )
    parser.add_argument(
        "--check-follow-me",
        action="store_true",
        help="Check if users you follow are following you back",
    )

    args = parser.parse_args()

    if args.check_follow_me:
        check_follow_me_back(args.profile_username)
    else:
        fetch_and_save_data(args.profile_username)


if __name__ == "__main__":
    main()
    conn.close()
