"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import json
import os
from pathlib import Path
import tempfile
from threading import Lock

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
registrations_file = Path(os.environ.get(
    "ACTIVITY_REGISTRATIONS_FILE", current_dir / "registrations.json"))
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

registrations_lock = Lock()


def load_registrations():
    """Restore saved participant lists, leaving defaults for new activities."""
    if not registrations_file.exists():
        return

    try:
        saved_registrations = json.loads(
            registrations_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Unable to load registrations from {registrations_file}") from error

    if not isinstance(saved_registrations, dict):
        raise RuntimeError(
            f"Invalid registrations data in {registrations_file}: expected an object")

    for activity_name, participants in saved_registrations.items():
        if (activity_name not in activities
                or not isinstance(participants, list)
                or any(not isinstance(email, str) for email in participants)
                or len(participants) != len(set(participants))):
            raise RuntimeError(
                f"Invalid registrations data for {activity_name!r} "
                f"in {registrations_file}")
        activities[activity_name]["participants"] = participants


def save_registrations():
    """Atomically persist participant lists so interrupted writes cannot corrupt them."""
    registrations_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=registrations_file.parent,
        prefix=f".{registrations_file.name}.",
        suffix=".tmp",
        delete=False
    )
    try:
        with temporary_file:
            json.dump(
                {name: activity["participants"]
                 for name, activity in activities.items()},
                temporary_file,
                indent=2
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_file.name, registrations_file)
    except Exception:
        try:
            os.unlink(temporary_file.name)
        except FileNotFoundError:
            pass
        raise


load_registrations()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with registrations_lock:
        if activity_name not in activities:
            raise HTTPException(status_code=404, detail="Activity not found")

        activity = activities[activity_name]

        if email in activity["participants"]:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        if len(activity["participants"]) >= activity["max_participants"]:
            raise HTTPException(status_code=400, detail="Activity is full")

        activity["participants"].append(email)
        try:
            save_registrations()
        except Exception:
            activity["participants"].pop()
            raise

        return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with registrations_lock:
        if activity_name not in activities:
            raise HTTPException(status_code=404, detail="Activity not found")

        activity = activities[activity_name]

        if email not in activity["participants"]:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        participant_index = activity["participants"].index(email)
        activity["participants"].pop(participant_index)
        try:
            save_registrations()
        except Exception:
            activity["participants"].insert(participant_index, email)
            raise

        return {"message": f"Unregistered {email} from {activity_name}"}
