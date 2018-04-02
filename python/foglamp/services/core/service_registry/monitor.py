# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Monitor module"""

import asyncio
import aiohttp
import json
from foglamp.common import logger
from foglamp.common.audit_logger import AuditLogger
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.common.service_record import ServiceRecord
from foglamp.services.core import connect

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Monitor(object):

    _DEFAULT_SLEEP_INTERVAL = 5
    """The time (in seconds) to sleep between health checks"""

    _DEFAULT_PING_TIMEOUT = 1
    """Timeout for a response from any given micro-service"""

    _DEFAULT_MAX_ATTEMPTS = 15

    _logger = None

    def __init__(self):
        self._logger = logger.setup(__name__, level=20)

        self._monitor_loop_task = None  # type: asyncio.Task
        """Task for :meth:`_monitor_loop`, to ensure it has finished"""
        self._sleep_interval = None  # type: int
        """The time (in seconds) to sleep between health checks"""
        self._ping_timeout = None  # type: int
        """Timeout for a response from any given micro-service"""
        self._max_attempts = None  # type: int
        """Number of max attempts for finding a heartbeat of service"""

    async def _sleep(self, sleep_time):
        await asyncio.sleep(sleep_time)

    async def _monitor_loop(self):
        """async Monitor loop to monitor registered services"""
        # check health of all micro-services every N seconds
        round_cnt = 0
        while True:
            round_cnt += 1
            self._logger.info("Starting next round#{} of service monitoring, sleep/i:{} ping/t:{} max/a:{}".format(
                round_cnt, self._sleep_interval, self._ping_timeout, self._max_attempts))
            for service_record in ServiceRegistry.all():
                # Try ping if service status is either running or doubtful (i.e. give service a chance to recover)
                if service_record._status not in [ServiceRecord.Status.Running, ServiceRecord.Status.Doubtful]:
                    continue
                try:
                    url = "{}://{}:{}/foglamp/service/ping".format(
                        service_record._protocol, service_record._address, service_record._management_port)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=self._ping_timeout) as resp:
                            text = await resp.text()
                            res = json.loads(text)
                            if res["uptime"] is None:
                                raise ValueError('Improper Response')
                except:  # TODO: Fix too broad exception clause
                    service_record._status = ServiceRecord.Status.Doubtful
                    service_record._check_count += 1
                    self._logger.info("Marked as doubtful micro-service %s", service_record.__repr__())
                else:
                    service_record._status = ServiceRecord.Status.Running
                    service_record._check_count = 1

                if service_record._check_count > self._max_attempts:
                    ServiceRegistry.mark_as_failed(service_record._id)
                    try:
                        audit = AuditLogger(connect.get_storage())
                        await audit.failure('SRVFL', {'name':service_record._name})
                    except Exception as ex:
                        self._logger.info("Failed to audit service failure %s", str(ex));
            await self._sleep(self._sleep_interval)

    async def _read_config(self):
        """Reads configuration"""
        default_config = {
            "sleep_interval": {
                "description": "The time (in seconds) to sleep between health checks. (must be greater than 5)",
                "type": "integer",
                "default": str(self._DEFAULT_SLEEP_INTERVAL)
            },
            "ping_timeout": {
                "description": "Timeout for a response from any given micro-service. (must be greater than 0)",
                "type": "integer",
                "default": str(self._DEFAULT_PING_TIMEOUT)
            },
            "max_attempts": {
                "description": "Number of max attempts for finding a heartbeat of service",
                "type": "integer",
                "default": str(self._DEFAULT_MAX_ATTEMPTS)
            },
        }

        storage_client = connect.get_storage()
        cfg_manager = ConfigurationManager(storage_client)
        await cfg_manager.create_category('SMNTR', default_config, 'Service Monitor configuration')

        config = await cfg_manager.get_category_all_items('SMNTR')

        self._sleep_interval = int(config['sleep_interval']['value'])
        self._ping_timeout = int(config['ping_timeout']['value'])
        self._max_attempts = int(config['max_attempts']['value'])

    async def start(self):
        await self._read_config()
        self._monitor_loop_task = asyncio.ensure_future(self._monitor_loop())

    async def stop(self):
        self._monitor_loop_task.cancel()
