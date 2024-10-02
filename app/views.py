from flask import Blueprint, render_template, jsonify
from app import db
from sqlalchemy import text

# Blueprint definition
main_blueprint = Blueprint('main', __name__)


# Root route - could be your dashboard
@main_blueprint.route('/')
def index():
    return render_template('dashboard.html')


# Web UI route for the server details page
@main_blueprint.route('/server')
def server():
    return render_template('server.html')


# Web UI route for the server details page
@main_blueprint.route('/overview')
def overview():
    return render_template('serverOverview.html')


@main_blueprint.route('/process&threads')
def processnthreads():
    return render_template('process&threads.html')

@main_blueprint.route('/serverNetwork')
def serverNetwork():
    return render_template('serverNetwork.html')

# Web UI route for the server details page
@main_blueprint.route('/rules')
def rules():
    return render_template('rules.html')

