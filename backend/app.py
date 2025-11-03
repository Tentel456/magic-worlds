import os
from . import create_app


def _config_name():
    return os.environ.get("FLASK_ENV", "development")


app = create_app(_config_name())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
