# extending grafanalib from https://github.com/weaveworks/grafanalib

__version__ = "0.1.0"

import json
import random
from string import ascii_lowercase, ascii_uppercase, digits
import attr
import grafanalib.core as gf
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from requests.status_codes import codes as request_codes
from grafanalib.core import (
    Time,
    Templating,
    Template,
    Row,
    TABLE_TARGET_FORMAT,
    Target,
    single_y_axis,
    ColumnStyle,
)
from grafanalib._gen import DashboardEncoder
from attr.validators import instance_of
from os import environ


def get_http_auth():
    return HTTPBasicAuth("IGZGrafanaAdmin", "IGZGrafanaAdmin123!")


@attr.s
class ExtendedTarget(Target):

    type = attr.ib(default="table")

    def to_json_data(self):
        retval = super(ExtendedTarget, self).to_json_data()
        retval["type"] = self.type
        return retval


@attr.s
class DashboardImport(object):
    dashboard = attr.ib(default="")
    inputs = attr.ib(default=attr.Factory(list))
    overwrite = attr.ib(validator=instance_of(bool), default=True)

    def to_json_data(self):
        return {
            "dashboard": self.dashboard,
            "inputs": self.inputs,
            "overwrite": self.overwrite,
        }


@attr.s
class ExtendedColumnStyle(ColumnStyle):
    link = attr.ib(validator=instance_of(bool), default=False)
    link_url = attr.ib("")
    link_tooltip = attr.ib("")

    def to_json_data(self):
        retval = super(ExtendedColumnStyle, self).to_json_data()
        if self.link:
            retval.update(
                {
                    "link": self.link,
                    "linkUrl": self.link_url,
                    "linkTooltip": self.link_tooltip,
                }
            )
        return retval


@attr.s
class Ajax(object):
    """
    Generates Ajax panel

    :param dataSource: Grafana datasource name
    :param title: panel title
    :param url: target url
    :param editable: defines if panel is editable via web interfaces
    :param span: defines the number of spans that will be used for panel
    :param mode: defines the display mode (json)
    :param method: http method GET/POST/iframe
    """

    dataSource = attr.ib(default=None)
    targets = attr.ib(default=attr.Factory(list))
    title = attr.ib(default="")
    header_js = attr.ib(default="{}")
    editable = attr.ib(default=True, validator=instance_of(bool))
    id = attr.ib(default=None)
    links = attr.ib(default=attr.Factory(list))
    showTime = attr.ib(default=False, validator=instance_of(bool))
    responseType = attr.ib(default="text")
    params_js = attr.ib(default="{}",)
    showTimeFormat = attr.ib(default="LTS")
    showTimePrefix = attr.ib(default=None)
    showTimeValue = attr.ib(default="request")
    skipSameURL = attr.ib(default=True, validator=instance_of(bool))
    method = attr.ib(default="GET")
    mode = attr.ib(default="json")
    withCredentials = attr.ib(default=False, validator=instance_of(bool))
    url = attr.ib(default="")
    template = attr.ib(default="")
    span = attr.ib(default=6)

    def to_json_data(self):
        return {
            "dataSource": self.dataSource,
            "targets": self.targets,
            "title": self.title,
            "editable": self.editable,
            "id": self.id,
            "links": self.links,
            "showTime": self.showTime,
            "responseType": self.responseType,
            "params_js": self.params_js,
            "showTimeFormat": self.showTimeFormat,
            "showTimePrefix": self.showTimePrefix,
            "showTimeValue": self.showTimeValue,
            "skipSameURL": self.skipSameURL,
            "method": self.method,
            "mode": self.mode,
            "withCredentials": self.withCredentials,
            "url": self.url,
            "template": self.template,
            "type": "ryantxu-ajax-panel",
        }


_query_separator = ";"


@attr.s
class Dashboard(gf.Dashboard):
    """Generates Dashboard object

    :param title: panel title
    :param dataSource: Grafana datasource name
    :param start: start time, e.g. now-1d
    :param end: end time, e.g. now
    """

    rows = attr.ib(default=attr.Factory(list))
    start = attr.ib(default="now-1h")
    end = attr.ib(default="now")
    templates = attr.ib(default=attr.Factory(list))
    dataSource = attr.ib(default="iguazio")
    backend = attr.ib(default="")
    container = attr.ib(default="")

    def row(self, elements=None, **kw):
        elements = elements or []
        panels = []
        for element in elements:
            element.dataSource = getattr(element, "dataSource", "") or self.dataSource
            panels += [element]
        self.rows += [Row(panels=panels, **kw)]
        return self

    def template(self, name, frame=None, type="query", query="", **kw):
        kw["dataSource"] = getattr(kw, "dataSource", "") or self.dataSource
        if frame and not query:
            query = frame.gen_target
        self.templates += [Template(name=name, type=type, query=query, **kw)]
        return self

    def show(self):
        return self.__generate()

    def deploy(self, url, user="", password=""):

        auth = get_http_auth() if not (user and password) else None

        res = requests.post(
            url="{}/api/dashboards/import".format(url),
            data=self.__generate(),
            auth=auth,
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "x-remote-user": environ.get("V3IO_USERNAME", "admin"),
            },
        )
        res.raise_for_status()
        print("Dashboard {} created successfully".format(self.title))

    def __generate(self):

        self.uid = "".join(random.choice(ascii_lowercase + digits) for _ in range(10))
        self.time = Time(start=self.start, end=self.end)
        self.templating = Templating(self.templates)
        dashboard = self.auto_panel_ids()

        dashboard_import = DashboardImport(dashboard=dashboard)
        return json.dumps(
            dashboard_import.to_json_data(),
            sort_keys=True,
            indent=2,
            cls=DashboardEncoder,
        )


@attr.s
class DataFrame(object):

    backend = attr.ib()
    container = attr.ib(default="")
    query = attr.ib(default="")
    table = attr.ib(default="")
    filter = attr.ib(default="")
    fields = attr.ib(default=[])

    def gen_target(self):
        target = [
            "table=" + self.table,
            "fields={}".format(",".join(self.fields)),
            "backend=" + self.backend,
            "container=" + self.container,
        ]

        if self.filter:
            target += ["filter=" + self.filter]

        if self.query:
            target += ["query=" + self.query]

        return _query_separator.join(target)


@attr.s
class Table(gf.Table):
    """Generates Table panel json structure

    Grafana doc on table: http://docs.grafana.org/reference/table_panel/

    :param columns: table columns for Aggregations view
    :param dataSource: Grafana datasource name
    :param description: optional panel description
    :param editable: defines if panel is editable via web interfaces
    :param fontSize: defines value font size
    :param height: defines panel height
    :param hideTimeOverride: hides time overrides
    :param id: panel id
    :param links: additional web links
    :param minSpan: minimum span number
    :param pageSize: rows per page (None is unlimited)
    :param scroll: scroll the table instead of displaying in full
    :param showHeader: show the table header
    :param span: defines the number of spans that will be used for panel
    :param styles: defines formatting for each column
    :param targets: list of metric requests for chosen datasource
    :param timeFrom: time range that Override relative time
    :param title: panel title
    :param transform: table style
    :param transparent: defines if panel should be transparent
    """

    dataSource = attr.ib(default="")
    targets = attr.ib(default=[])
    transform = attr.ib(default="table_to_columns")

    def source(self, **kw):
        kw["backend"] = getattr(kw, "backend", "kv")
        self.targets.append(
            ExtendedTarget(
                expr="",
                legendFormat="1xx",
                refId=random.choice(ascii_uppercase),
                target=DataFrame(**kw).gen_target(),
                format=TABLE_TARGET_FORMAT,
                type="table",
            )
        )
        return self


@attr.s
class Graph(gf.Graph):
    """Generates Graph panel json structure

    Grafana doc on table: http://docs.grafana.org/features/panels/graph/

    :param dataSource: Grafana datasource name
    :param description: optional panel description
    :param editable: defines if panel is editable via web interfaces
    :param fontSize: defines value font size
    :param height: defines panel height
    :param links: additional web links
    :param showHeader: show the table header
    :param span: defines the number of spans that will be used for panel
    :param targets: list of metric requests for chosen datasource
    :param timeFrom: time range that Override relative time
    :param title: panel title
    :param transparent: defines if panel should be transparent
    :param minSpan: Minimum width for each panel
    :param repeat: Template's name to repeat Graph on
    """

    targets = attr.ib(default=[])
    _last_target = attr.ib(default=0)

    def yaxis(self, **kw):
        self.yAxes = gf.YAxes(left=gf.YAxis(**kw))

    def series(self, expr="", legendFormat="1xx", **kw):

        ref_id = ascii_uppercase[self._last_target]
        self._last_target += 1

        if expr:
            self.targets = [
                ExtendedTarget(
                    expr=expr,
                    format="time_series",
                    refId=ref_id,
                    legendFormat=legendFormat,
                    type="timeserie",
                )
            ]
        else:

            kw["backend"] = getattr(kw, "backend", "tsdb")

            self.targets = [
                ExtendedTarget(
                    expr="",
                    format="time_series",
                    target=DataFrame(**kw).gen_target(),
                    refId=ref_id,
                    legendFormat=legendFormat,
                    type="timeserie",
                )
            ]

        return self


@attr.s
class DataSource(object):

    name = attr.ib(default="iguazio")
    frames_url = attr.ib(default="http://framesd:8080")
    frames_user = attr.ib(default="")
    frames_password = attr.ib(default="")
    frames_accesskey = attr.ib(default="")
    use_auth = attr.ib(default=True)

    def deploy(self, url, user="", password="", overwrite=False, use_auth=None):

        data_dict = dict(
            name=self.name,
            type="grafana-simple-json-datasource",
            url=self.frames_url,
            access="proxy",
        )

        auth = get_http_auth()
        if user and password:
            auth = HTTPBasicAuth(user, password)

        if use_auth or (use_auth is None and self.use_auth):
            auth_dict = dict(
                basicAuth=True,
                basicAuthUser=self.frames_user or "__ACCESS_KEY",
                basicAuthPassword=self.frames_accesskey
                or environ.get("V3IO_ACCESS_KEY"),
            )
            data_dict.update(auth_dict)

        kw = dict(
            url="{}/api/datasources".format(url),
            verify=False,
            data=json.dumps(data_dict),
            auth=auth,
            headers={
                "content-type": "application/json",
                "x-remote-user": environ.get("V3IO_USERNAME", "admin"),
            },
        )

        res = requests.post(**kw)
        try:
            res.raise_for_status()
        except HTTPError:
            if res.status_code == request_codes.conflict:
                print("Datasource {} already exists".format(self.name))
                if overwrite:
                    print("Recreating datasource {}".format(self.name))
                    res = requests.delete(
                        url="{}/api/datasources/name/{}".format(
                            self.__grafana_url, self.name
                        ),
                        verify=False,
                        auth=HTTPBasicAuth(*self.__auth),
                    )
                    res.raise_for_status()
                    res = requests.post(**kw)
                    res.raise_for_status()
            else:
                raise
        print("Datasource {} created successfully".format(self.name))
