from app import create_app
from werkzeug.serving import run_simple
import os


config_name = os.getenv("APP_SETTINGS")
app = create_app(config_name)


if __name__ == "__main__":
    # app.run()
    run_simple('localhost', 5000, app,
               use_reloader=True, use_debugger=True, use_evalex=True)
