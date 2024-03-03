import logging

from flask import Flask, request, render_template

# Function to verify the signature
# To ensure that the payload was sent from GitHub
from workers.webhook_validator import WebhookValidator

from workers.database import DBWorker

app = Flask(__name__)


# Configure Flask logging
app.logger.setLevel(logging.INFO)  # Set log level to INFO
handler = logging.FileHandler("flask-app.log")  # Log to a file
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
app.logger.addHandler(handler)

TARGET_BRANCH = "main"


@app.route("/")
def index():
    db_worker = DBWorker()
    statistics: dict = db_worker.get_tests_statistics()
    all_projects: list[dict] = db_worker.get_all_projects()

    return render_template("index.html", statistics=statistics, projects=all_projects)


@app.route("/project/<int:project_id>")
def project(project_id):
    db_worker = DBWorker()
    project: tuple = db_worker.get_project_by_id(project_id)
    project_stats: dict = db_worker.get_project_statistics(project_id)
    test_batches: dict = db_worker.get_project_test_batches(project_id)

    return render_template("project.html", project=project, test_batches=test_batches, stats=project_stats)


@app.route("/test", methods=["POST"])
def test():
    """
    Flask route to trigger the test process.

    """

    json_body = request.json
    branch = json_body["ref"].split("/")[-1]

    if branch != TARGET_BRANCH:
        return {"status": "success", "message": "not target branch"}

    secret_header = request.headers.get("X-Hub-Signature-256")
    payload = request.data

    if WebhookValidator.verify_signature(
        payload_body=payload,
        signature_header=secret_header,
    ):

        # Call the test script

        return {"status": "success", "message": "test process triggered"}

    else:
        return {"status": "error", "message": "Invalid signature"}


@app.route("/add_project", methods=["POST"])
def add_project():
    """
    Flask route to add a new project to the database.

    """
    db_worker = DBWorker()

    json_body = request.json
    target_branch = json_body.get("target_branch", "main")

    name, test_file, github_url = (
        json_body["name"],
        json_body["test_file"],
        json_body["github_url"],
        target_branch,
    )

    db_worker.insert_project_to_database(name, test_file, github_url, target_branch)

    return {"status": "success", "message": "project added"}


# @app.errorhandler(500)
# def server_error(error):
#     app.logger.exception('An exception occurred during a request.')
#     return 'Internal Server Error', 500


if __name__ == "__main__":
    app.run(debug=True)
