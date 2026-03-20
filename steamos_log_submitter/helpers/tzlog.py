#!/usr/bin/python
# SPDX-License-Identifier: LGPL-2.1-or-later
# vim:ts=4:sw=4:et
#
# Copyright (c) 2026 Valve Software

import datetime
import os
import zipfile

import steamos_log_submitter as sls
from steamos_log_submitter.aggregators.sentry import SentryEvent
from steamos_log_submitter.helpers import Helper, HelperResult

class TzlogHelper(Helper):

    @classmethod
    async def collect(cls) -> list[str]:
        tzdbg = '/proc/tzdbg'

        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y%m%d%H%M%S")
        zip_filename = f"tzlog-{formatted_time}.zip"

        with sls.helpers.StagingFile('tzlog', zip_filename, 'wb') as f:
            with zipfile.ZipFile(f, mode='x', compression=zipfile.ZIP_DEFLATED) as zf:
                for tzfile in os.listdir(tzdbg):
                    file = sls.util.read_file(f'{tzdbg}/{tzfile}')
                    zip_info = zipfile.ZipInfo(f'{tzfile}.log')
                    zip_info.date_time = current_time.timetuple()[:6] 

                    if file:
                        zf.writestr(zip_info, file)

        return await super().collect()

    @classmethod
    async def submit(cls, fname: str) -> HelperResult:

        try:
            with open(fname, 'rb') as f:
                attachment = f.read()
        except zipfile.BadZipFile:
            return HelperResult.PERMANENT_ERROR
        except OSError:
            return HelperResult.TRANSIENT_ERROR

        basename = os.path.basename(fname)
        event = SentryEvent(cls.config['dsn'])
        event.add_attachment({
            'mime-type': 'application/zip',
            'filename': f'{basename}',
            'data': attachment
        })
        event.message = "TZlog collection"

        return HelperResult.check(await event.send())
