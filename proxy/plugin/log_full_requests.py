# -*- coding: utf-8 -*-
"""
    proxy.py
    ~~~~~~~~
    ⚡⚡⚡ Fast, Lightweight, Pluggable, TLS interception capable proxy server focused on
    Network monitoring, controls & Application development, testing, debugging.

    :copyright: (c) 2013-present by Abhinav Singh and contributors.
    :license: BSD, see LICENSE for more details.
"""

import logging
from typing import Optional, Any

from ..common.flag import flags
from ..common.utils import build_http_response
from ..http.parser import HttpParser, httpParserStates, httpParserTypes
from ..http.codes import httpStatusCodes
from ..http.proxy import HttpProxyBasePlugin
import yaml
import json


logger = logging.getLogger(__name__)
import arrow
import os

flags.add_argument(
        "--log-dir",
        type=str,
        default="/tmp/request-logs",
        help="location where to store the full request/response log"
)

class LogAllRequestsPlugin(HttpProxyBasePlugin):
    """Logs complete requests/responses to file"""
    WHITELIST = ['blog.fefe.de',
                 'postman-echo.com', 
                 'httpbin.org', 
                ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.response = HttpParser(httpParserTypes.RESPONSE_PARSER)
        self.log_full = True

    def before_upstream_connection(
            self, request: HttpParser) -> Optional[HttpParser]:
        if request.host.decode() not in self.WHITELIST:
            self.log_full = False
            return request
        
        request_line = "{} {} {}\n".format(request.method.decode(),
                                           request.path.decode(),
                                           request.version.decode())
        self.log_file_full = "{}/{} - {} - {} {}.log".format(self.flags.log_dir,
                                               arrow.now().format("DD.MM.YYYY-HHmmss"),
                                               request.host.decode(),
                                               request.method.decode(),
                                               request.path.decode().replace("/", "|"))
        with open(self.log_file_full, "w") as f:
            f.write(request_line)
            for __, header in request.headers.items():
                header_name, header_value = header
                f.write("{}: {}\n".format(header_name.decode(), header_value.decode()))
            if request.body:
                f.write("\n{}".format(request.body.decode()))

        return request

    def handle_client_request(
            self, request: HttpParser) -> Optional[HttpParser]:
        return request

    def handle_upstream_chunk(self, chunk: memoryview) -> memoryview:
        self.response.parse(chunk.tobytes())
        if self.response.state == httpParserStates.COMPLETE:
            if not self.log_full:
                return chunk
            
            response_line = "{} {} {}\n".format(self.response.version.decode(),
                                              self.response.code.decode(),
                                              self.response.reason.decode())
            with open(self.log_file_full, "a") as f:
                f.write("\n=========================== BEGIN RESPONSE ===========================\n\n")
                f.write(response_line)
                for __, header in self.response.headers.items():
                    header_name, header_value = header
                    f.write("{}: {}\n".format(header_name.decode(), header_value.decode()))
                if b"application/json" in self.response.headers[b'content-type'][1]:
                    j = json.loads(self.response.body.decode())
                    f.write("\n{}".format(json.dumps(j, indent=4, sort_keys=True)))
                else:
                    f.write("\n{}".format(self.response.body.decode()))
        return chunk

    def on_upstream_connection_close(self) -> None:
        pass

