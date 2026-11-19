# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 François Dausseur
"""Generic access to the RPC link of a subprocess engine."""

from runtime.tum_except import ETUMRuntimeError


class RpcEngineMixin:
    """For the process bases holding ``_rpc`` and ``_req_handler``."""

    def call(self, method, params, timeout=None):
        """Call a method of the worker and return its raw answer."""
        if self._rpc is None or not self._rpc.is_alive():
            raise ETUMRuntimeError(
                f"Cannot send the '{method}' call: the subprocess is not "
                "running.")
        if timeout is None:
            return self._rpc.call(method, params)
        return self._rpc.call(method, params, timeout)

    def set_request_handler(self, handler):
        """Replace the handler of the worker requests. Returns the old one."""
        old = self._req_handler
        self._req_handler = handler
        if self._rpc is not None:
            self._rpc._req_handler = handler
        return old
