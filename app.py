import streamlit as st
import pandas as pd
from dataclasses import dataclass, asdict
from typing import TypedDict
import json
from supabase import create_client, Client

# --- Configuration and Constants ---
REPORTS_FILE = "./data/reports.json"
USERS_FILE = "./data/users.csv"
STATE_TABLE = "state"
ANNOTATIONS_TABLE = "annotations"


@dataclass
class State:
    report_id: int
    user_id: int
    show_tutorial: bool


class Annotation(TypedDict):
    user_id: int
    relevant_reports: list[int]


STATE_ROW_ID = st.secrets["STATE_ROW_ID"]  # The fixed primary key of the state row
ANNOTATIONS_ROW_ID = st.secrets[
    "ANNOTATIONS_ROW_ID"
]  # The fixed primary key of the state row
DEFAULT_STATE = State(report_id=0, user_id=0, show_tutorial=True)


# Initialize Supabase client
@st.cache_resource
def init_supabase_client():
    """Initializes and returns the Supabase client."""
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase: Client = init_supabase_client()


def load_state() -> State:
    """Loads the application state (report and user index) from the Supabase database."""
    try:
        # Query the database for the single state row
        response = (
            supabase.table(STATE_TABLE).select("*").eq("id", STATE_ROW_ID).execute()
        )

        # Check if data was returned
        if response.data and len(response.data) > 0:
            state_data = response.data[0]
            # Convert values to int for session_state consistency
            return State(
                report_id=int(state_data.get("report_id", 0)),
                user_id=int(state_data.get("user_id", 0)),
                show_tutorial=state_data.get("show_tutorial", True),
            )
        else:
            print(response)
            raise RuntimeError("State row not found")

    except Exception as e:
        st.error(f"Error loading state from Supabase: {e}")
        raise e


def save_state(state: State):
    """Saves the current application state to the Supabase database and updates session_state."""
    new_state: dict = asdict(state)
    print(f"Saving state: {new_state}")
    try:
        # Update the single state row based on its fixed ID
        supabase.table(STATE_TABLE).update(new_state).eq("id", STATE_ROW_ID).execute()

    except Exception as e:
        # It's helpful to log or display a temporary error if saving fails
        print(f"Error saving state to Supabase: {e}")
        st.toast("Warning: Could not save progress to database!", icon="⚠️")
        raise e


def load_data():
    """Loads reports and users from their respective files."""
    with open(REPORTS_FILE, "r", encoding="utf-8") as f:
        reports = json.load(f)
    users = pd.read_csv(USERS_FILE)
    return reports, users


def load_annotations(users: pd.DataFrame) -> dict[int, Annotation]:
    try:
        # Query the database for the single state row
        response = (
            supabase.table(ANNOTATIONS_TABLE)
            .select("*")
            .eq("id", ANNOTATIONS_ROW_ID)
            .execute()
        )
        # Check if data was returned
        if response.data and len(response.data) > 0:
            # Convert values to int for session_state consistency
            annotations_dict: dict[int, Annotation] = response.data[0].get("data", {})
            if not annotations_dict:
                return {
                    row["user_id"]: {"relevant_reports": []}
                    for _, row in users.iterrows()
                }
            else:
                return annotations_dict
        else:
            raise RuntimeError("Annotation data row not found")

    except Exception as e:
        st.error(f"Error loading annoations data from Supabase: {e}")
        raise e


def save_annotation(annotations: dict[int, Annotation], user_id: int, report_id: int):
    """Adds a relevant report ID to a given user and saves the file."""
    # Ensure we don't add duplicates
    if report_id not in annotations[user_id]["relevant_reports"]:
        annotations[user_id]["relevant_reports"].append(report_id)
        annotations[user_id]["relevant_reports"] = list(
            set(annotations[user_id]["relevant_reports"])
        )
    try:
        # Update the single state row based on its fixed ID
        supabase.table(ANNOTATIONS_TABLE).update({"data": annotations}).eq(
            "id", ANNOTATIONS_ROW_ID
        ).execute()

    except Exception as e:
        # It's helpful to log or display a temporary error if saving fails
        print(f"Error saving annotations to Supabase: {e}")
        st.toast("Warning: Could not save progress to database!", icon="⚠️")
        raise e


# --- Main application function ---


def main():
    st.set_page_config(layout="wide", page_title="CTI Annotation Tool")

    st.markdown(
        """
    <style>
    [data-testid="stMarkdownContainer"] ul{
        padding-left:20px;
    }

    .stMainBlockContainer  {
        padding-top: 3rem;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Load data
    reports, users = load_data()
    total_reports = len(reports)
    total_users = len(users)

    # Load state
    state: State = load_state()
    # Load annotations
    annotations: dict[int, Annotation] = load_annotations(users)

    # Get the current report and user
    current_report = reports[state.report_id]
    current_user = users.iloc[state.user_id]

    # Check if the state file exists and if 'welcome_shown' is not in the session state
    if state.show_tutorial:
        # Display a title
        st.title("Welcome to the data annotation tool! 👋")

        # Display a markdown block with instructions
        st.markdown(
            """
            This application is designed to easily annotate CTI reports relevance for a given user.
            ### How to use the application?

            It's simple! Your task is to evaluate whether a given CTI report is relevant for the displayed user.

            1. **On the left side** you will find the full content of the report to analyze.

            2. **On the right side** you can see the detailed user profile for whom you are making the evaluation.

            3. **At the bottom** use one of the two buttons:

                * **✅ Relevant**: Click if you believe the report is important for this user.

                * **❌ Irrelevant**: Click if the report is not important.

            The application automatically **saves your progress** after each click and moves on to the next task. You can close it at any time and come back to the same place later.
            You can also see a progress bar at the top to keep track of the whole annotation process.

            Once you have finished annotating all reports you can click the "Download results" button at the bottom of the page to download the results as a JSON file.
            """
        )

        # If the "Let's start!" button is clicked
        if st.button(
            "Let's start annotating!", use_container_width=True, type="primary"
        ):
            state.show_tutorial = False
            state.report_id = 10
            save_state(state)

            # Rerun the app to show the main application
            st.rerun()

        # Stop further code execution until the button is pressed
        return

    # Check if annotation is complete
    if state.report_id >= total_reports:
        st.success("🎉 Congratulations! All reports have been annotated. Please write us a message to let us now you've finished.")
        st.balloons()
        return

    # --- User Interface ---

    # Display progress
    st.info(
        f"Progress: Report {state.report_id + 1} of {total_reports} | User {state.user_id + 1} of {total_users}"
    )
    st.progress(
        (state.report_id * total_users + state.user_id) / (total_reports * total_users)
    )

    col1, col2 = st.columns(2)

    # Left column: Report details
    with col1:
        st.subheader(f"Report: {current_report['title']}")
        st.caption(
            f"ID: {current_report['id']} | Creation Date: {current_report['creation_date']}"
        )

        # Create a scrollable container for the description
        st.markdown(
            f"""
            <div style="height: 420px; overflow-y: scroll; border: 1px solid #e6e6e6; padding: 10px; border-radius: 5px;">
            {current_report['description']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Right column: User data
    with col2:
        st.subheader(f"User: {current_user['name']}")
        st.caption(f"ID: {current_user['user_id']}")

        for key, value in current_user.items():
            if key not in ["user_id", "name"]:
                item_header = f"**{key.replace('_', ' ').capitalize()}:** "
                # Split values by semicolon and display as a list
                items = str(value).split(";")
                if len(items) > 1:
                    st.markdown(
                        item_header + ", ".join([f"{item.strip()}" for item in items])
                    )
                else:
                    st.write(item_header + value)

    st.markdown("---")  # Separator

    # Annotation buttons
    btn_col1, btn_col2, _ = st.columns([1, 1, 2])  # The last column is a "filler"

    is_relevant = btn_col1.button(
        "✅ Relevant", use_container_width=True, type="primary"
    )
    is_not_relevant = btn_col2.button("❌ Not Relevant", use_container_width=True, width=100)

    # --- Logic after button click ---

    if is_relevant or is_not_relevant:
        if is_relevant:
            # Load, update, and save annotations
            annotations = load_annotations(users)
            save_annotation(annotations, current_user["user_id"], current_report["id"])

        # Move to the next user or report
        state.user_id += 1
        if state.user_id >= total_users:
            state.user_id = 0
            state.report_id += 1

        # Save the new state and rerun the app
        save_state(state)
        st.rerun()

    # results = {
    #     "state": asdict(state),
    #     "annotations": annotations,
    # }
    # results = json.dumps(results, indent=2)
    # if st.download_button(
    #     label="Download results",
    #     data=results,
    #     type="secondary",
    #     file_name="annotations.json",
    #     mime="application/json",
    #     icon=":material/download:",
    # ):
    #     st.toast(
    #         "Thank you! Please send this file to cezary.maszczyk@ai.lukasiewicz.gov.pl.",
    #         icon="✅",
    #     )


if __name__ == "__main__":
    main()
