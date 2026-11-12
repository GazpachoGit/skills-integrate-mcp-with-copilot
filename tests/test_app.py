import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from src import app as activities_app


class RegistrationPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.original_participants = {
            name: activity["participants"][:]
            for name, activity in activities_app.activities.items()
        }
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.registrations_file = Path(self.temporary_directory.name) / "registrations.json"
        self.file_patch = patch.object(
            activities_app, "registrations_file", self.registrations_file)
        self.file_patch.start()

    def tearDown(self):
        self.file_patch.stop()
        for name, participants in self.original_participants.items():
            activities_app.activities[name]["participants"] = participants
        self.temporary_directory.cleanup()

    def test_signup_and_unregister_are_restored_from_disk(self):
        activity_name = "Chess Club"
        new_email = "new.student@mergington.edu"

        activities_app.signup_for_activity(activity_name, new_email)
        self.assertIn(new_email, json.loads(
            self.registrations_file.read_text(encoding="utf-8"))[activity_name])

        activities_app.activities[activity_name]["participants"] = (
            self.original_participants[activity_name][:]
        )
        activities_app.load_registrations()
        self.assertIn(new_email, activities_app.activities[activity_name]["participants"])

        activities_app.unregister_from_activity(activity_name, new_email)
        activities_app.activities[activity_name]["participants"] = (
            self.original_participants[activity_name][:]
        )
        activities_app.load_registrations()
        self.assertNotIn(new_email, activities_app.activities[activity_name]["participants"])

    def test_signup_rejects_full_activity_without_changing_roster(self):
        activity_name = "Chess Club"
        activity = activities_app.activities[activity_name]
        activity["participants"] = [
            f"student{index}@mergington.edu"
            for index in range(activity["max_participants"])
        ]
        participants_before = activity["participants"][:]

        with self.assertRaises(HTTPException) as error:
            activities_app.signup_for_activity(
                activity_name, "new.student@mergington.edu")

        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.detail, "Activity is full")
        self.assertEqual(activity["participants"], participants_before)
        self.assertFalse(self.registrations_file.exists())


if __name__ == "__main__":
    unittest.main()
