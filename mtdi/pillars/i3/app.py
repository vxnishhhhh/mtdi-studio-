"""create_app: one content pack in, one running I³ interface out."""
import json
import logging
import pathlib

from dash import Dash, Input, Output, dcc, html
from flask import jsonify, request

from . import components as c
from . import pages
from .content import validate

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"
LOG = logging.getLogger("i3")

FONTS = ("https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500"
         "&family=Inter:wght@300;400;500;600&display=swap")


def create_app(content, state_provider=None, ask_handler=None, action_handler=None, state_poll_ms=1500,
               **dash_kwargs):
    """Build the Dash app for a content pack.

    content         dict in the content-pack format (see content/placeholder.json)
    state_provider  optional callable returning {bind_key: value | {"value", "state"}};
                    served at /i3/state and polled by the browser for live values
    ask_handler     optional callable (question, path) -> answer string for the
                    NVTRA dock; served at /i3/ask
    action_handler  optional callable (action, args) -> message string for
                    "actions" blocks; served at /i3/action
    """
    validate(content)
    brand = content["brand"]
    app = Dash(__name__, assets_folder=str(ASSETS), title=brand.get("name", "I³"),
               suppress_callback_exceptions=True, update_title=None, **dash_kwargs)

    config = {"landUrl": app.get_asset_url("land.json"), "statePollMs": state_poll_ms,
              "forceHomeOnLoad": bool(content.get("force_home_on_load", False))}
    if state_provider:
        config["stateUrl"] = "/i3/state"
    if ask_handler:
        config["askUrl"] = "/i3/ask"
    if action_handler:
        config["actionUrl"] = "/i3/action"

    # The config must exist before i3.js runs, and the home redirect must happen
    # before Dash reads location.pathname, so both go in <head>.
    force_home = ("<script>if(location.pathname!=='/'){try{history.replaceState(null,'','/'+location.search);}catch(e){}}"
                  "</script>") if config["forceHomeOnLoad"] else ""
    app.index_string = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    {{%metas%}}
    <title>{{%title%}}</title>
    {{%favicon%}}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="stylesheet" href="{FONTS}">
    {{%css%}}
    <meta name="theme-color" content="#07090f">
    <script>window.I3_CONFIG={json.dumps(config)};</script>
    {force_home}
  </head>
  <body>
    {{%app_entry%}}
    <footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
  </body>
</html>"""

    by_path = {p["path"]: p for p in content["pages"]}
    notice = content.get("notice")
    app.layout = html.Div([
        dcc.Location(id="i3-url", refresh=False),
        c.header(content),
        html.Div(notice, className="i3-notice") if notice else None,
        html.Div(brand.get("credit"), className="i3-credit") if brand.get("credit") else None,
        c.intro(content),
        c.dock(content),
        html.Div(html.Main(id="i3-page"), id="i3-shell"),
    ])

    @app.callback(Output("i3-page", "children"), Input("i3-url", "pathname"))
    def route(pathname):
        page = by_path.get(pathname or "/")
        if page is None:
            return html.Div([html.Div("404", className="i3-fw-kicker"),
                             html.H1("Nothing here.", className="i3-fw-title"),
                             dcc.Link(html.Button("← HOME", className="i3-btn-ghost"), href="/")],
                            className="i3-pad i3-doc")
        try:
            return pages.build(page, content)
        except Exception:
            LOG.exception("page build failed for %s", pathname)
            raise

    server = app.server
    if state_provider:
        @server.get("/i3/state")
        def _state():
            return jsonify(state_provider())

    if ask_handler:
        @server.post("/i3/ask")
        def _ask():
            body = request.get_json(silent=True) or {}
            question = str(body.get("question", ""))[:2000]
            return jsonify({"answer": ask_handler(question, body.get("path", "/"))})

    if action_handler:
        @server.post("/i3/action")
        def _action():
            body = request.get_json(silent=True) or {}
            try:
                message = action_handler(str(body.get("action", "")), body.get("args") or {})
                return jsonify({"ok": True, "message": message or "Done."})
            except (ValueError, KeyError, OSError) as error:
                return jsonify({"ok": False, "message": str(error).strip("'\"")}), 400

    return app
