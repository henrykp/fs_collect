import os
import logging
import uuid
import threading
import webbrowser
import datetime
from typing import Any
from typing import List
from typing import Optional
from typing import Dict

import msal
import flask
import requests
from flask import request
from werkzeug.serving import make_server

app = flask.Flask(__name__)
state = str(uuid.uuid4())
cache = msal.SerializableTokenCache()


@app.route("/msal")
def endpoint_auth() -> Any:
    if not request.args.get("state") == state:
        return flask.jsonify({"state": "error", "message": "Invalid request state"})

    if "error" in request.args:
        return flask.jsonify({"state": "error", **request.args})

    if request.args.get("code"):
        result = MicrosoftGraph.from_env()._acquire_token(request.args["code"])
        if "error" in result:
            return flask.jsonify({"state": "error", "message": result})

    _shutdown_after_request()
    return flask.jsonify({"state": "success", "message": "ok"})


class MicrosoftGraphError(Exception):
    pass


class Event:
    date_fmt = "%Y-%m-%dT%H:%M:%S.%f"

    def __init__(
        self,
        subject: str = "Working on some code",
        description: Optional[str] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
        with_reminder: bool = False,
    ) -> None:
        self.subject = subject
        self.description = description or ""
        self.start = start or datetime.datetime.now(datetime.timezone.utc)
        self.end = end or self.start + datetime.timedelta(minutes=15)
        self.with_reminder = with_reminder

        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise MicrosoftGraphError(
                "Unable to create an event with timezone unaware dates: "
                f"start: {self.start} end: {self.end} ({self.subject})"
            )

    def json(self) -> Dict[str, Any]:
        rv = {
            "subject": self.subject,
            "isReminderOn": self.with_reminder,
            "sensitivity": "personal",
            "showAs": "busy",
            "start": {
                "dateTime": self.start.strftime(self.date_fmt),
                "timeZone": self.start.tzname(),
            },
            "end": {
                "dateTime": self.end.strftime(self.date_fmt),
                "timeZone": self.end.tzname(),
            },
        }
        if self.description:
            rv["body"] = {"contentType": "HTML", "content": self.description}

        return rv


class MicrosoftGraph:
    __instance = None

    def __init__(self, client_id: str, client_secret: str, authority: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.authority = authority

        self._client: msal.ClientApplication = None
        self._cache = cache
        self._port = 8231
        self._host = "localhost"
        self._redirect_url = f"http://{self._host}:{self._port}/msal"
        self._scopes: List[str] = ["User.ReadBasic.All", "Calendars.ReadWrite"]

    @classmethod
    def from_env(cls) -> "MicrosoftGraph":
        if not cls.__instance:
            client_id = _osvar_or_err("MS_CLIENT_ID")
            client_secret = _osvar_or_err("MS_CLIENT_SECRET")
            authority = _osvar_or_err("MS_AUTHORITY")

            cls.__instance = MicrosoftGraph(
                client_id,
                client_secret,
                f"https://login.microsoftonline.com/{authority}",
            )

        return cls.__instance

    @property
    def client(self) -> msal.ClientApplication:
        if not self._client:
            self._client = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret,
                token_cache=self._cache,
            )

        return self._client

    @property
    def token(self) -> str:
        accounts = self.client.get_accounts()
        if not accounts:
            return ""

        token: Dict[str, str] = self.client.acquire_token_silent(
            self._scopes, accounts[0]
        )
        return token["access_token"]

    def _acquire_token(self, code: str) -> Dict[str, Any]:
        token_data: Dict[str, Any] = self.client.acquire_token_by_authorization_code(
            code, self._scopes, self._redirect_url
        )
        return token_data

    def authenticate(self) -> None:
        url = self.client.get_authorization_request_url(
            self._scopes, state=state, redirect_uri=self._redirect_url
        )
        server = make_server(self._host, self._port, app)
        app.app_context().push()
        srv = threading.Thread(target=server.serve_forever)
        srv.start()
        logging.info(url)
        webbrowser.open(url)
        srv.join()

    def schedule_meeting(self, event: Event) -> None:
        url = "https://graph.microsoft.com/v1.0/me/events"
        rv = requests.post(
            url, json=event.json(), headers={"Authorization": f"Bearer {self.token}"}
        )
        logging.debug(str(rv.json()))
        if rv.status_code not in (200, 201):
            raise MicrosoftGraphError(rv.json())


def _shutdown_after_request() -> None:
    q = request.environ.get("werkzeug.server.shutdown")
    if q is None:
        raise RuntimeError("Not running flask with Werkzeug!")
    q()


def _osvar_or_err(var: str) -> str:
    v = os.environ.get(var, None)
    if not v:
        raise MicrosoftGraphError(
            f"Environment variable {var} is not set. "
            "Please set it to an appropriate value and try again."
        )

    return v
