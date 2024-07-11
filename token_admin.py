import streamlit as st
import json
import os

# Function to read the token counts from a JSON file
def read_token_counts(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Function to write the token counts to a JSON file
def write_token_counts(file_path, token_counts):
    with open(file_path, "w") as f:
        json.dump(token_counts, f, indent=4)

def admin_app():
    st.title("Admin Panel for Token Management")

    # Get a list of JSON files in the current directory
    json_files = [f for f in os.listdir('.') if f.endswith('.json')]

    # Select a JSON file
    selected_file = st.selectbox("Select a JSON file", json_files)

    if selected_file:
        token_counts = read_token_counts(selected_file)

        st.write("Users and their token limits:")
        
        # Display users and their token limits
        for user, tokens in token_counts.items():
            new_token_limit = st.number_input(f"Tokens for {user}", min_value=0, value=tokens, key=user)
            token_counts[user] = new_token_limit

        if st.button("Save Changes"):
            write_token_counts(selected_file, token_counts)
            st.success("Token counts updated successfully")

if __name__ == "__main__":
    admin_app()
