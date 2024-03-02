import os
import subprocess

from database import DBWorker

from enums import ExitCodes

import xml.etree.ElementTree as ET


class Tester:
    """
    Run tests and parse results.
    """

    # Get the path of the current Python script
    __current_dir = os.path.dirname(os.path.abspath(__file__))
    __parent_dir = os.path.dirname(__current_dir)

    # Path to the bash_scripts directory
    __bash_scripts_dir = os.path.join(__parent_dir, "bash_scripts")

    __test_script_path = os.path.join(__bash_scripts_dir, "run_tests.sh")
    
    __db_worker = DBWorker()

    @classmethod
    def run_test_script(
        cls, project_name: str, test_file_name: str
    ) -> tuple[(ExitCodes, str)]:
        """
        Runs a bash script that creates a venv and installs project dependencies.

        The bash script then calls another bash script that run tests.

        Returns tuple with (success: Boolean, optional error message)

        Exit codes:
            see enums.py

        """
        return_code = subprocess.call(
            ["bash", cls.__test_script_path, project_name, test_file_name]
        )

        match return_code:
            case ExitCodes.SUCCESS.value:
                return (True,)
            case ExitCodes.MISSING_REQUIREMENTS.value:
                return (False, "requirements.txt does not exist")
            case ExitCodes.MISSING_TEST_FILE.value:
                return (False, "test file does not exist")
            case ExitCodes.VENV_CREATION_ERROR.value:
                return (False, "Could not create venv folder.")

    @classmethod
    def get_junitxml_file(cls, project_name: str) -> str:

        project_folder = os.path.join(cls.__parent_dir, "projects", project_name)

        xml_files = [
            file for file in os.listdir(project_folder) if file.endswith(".xml")
        ]
        # We take the first file in the list
        test_file = xml_files[0]

        test_file_path = os.path.join(project_folder, test_file)

        return test_file_path

    @classmethod
    def parse_junitxml_file(cls, project_name: str) -> None:

        # get_junitxml_file returns both the file name and the project folder path
        test_file_path = cls.get_junitxml_file(project_name)

        tree = ET.parse(test_file_path)
        root = tree.getroot()

        # Contains errors, failures, skipped, timestamp ...
        test_result = root[0].attrib

        # Extract the testcases
        testcases_elems = root[0].findall("testcase")
        testcases = (
            (elem.attrib["name"], elem.attrib["time"]) for elem in testcases_elems
        )

        parsed_data = {
            "project_name": project_name,
            "test_result": test_result,
            "testcases": testcases,
        }

        return parsed_data

    @classmethod
    def perform_tests(cls, project_name: str, test_file: str) -> list[dict]:
        """
        Run tests for a specific projects.

        Insert the result to the database.

        """

        # Run the test script
        success, error_message = cls.run_test_script(project_name, test_file)

        if success is False:
            return {"status": "error", "message": error_message}

        # Parse the junitxml file
        parsed_data = cls.parse_junitxml_file(project_name)
        
        cls.__db_worker.insert_project(project_name)

        return [parsed_data]
