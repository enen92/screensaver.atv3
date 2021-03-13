"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import hashlib
import json
import os
import time
from urllib.request import urlopen

import xbmc
import xbmcvfs

from .commonatv import *


class Downloader:

    def __init__(self, ):
        self.stop = False
        self.dp = None
        self.path = None

    # Given a list of URLs, attempt to download them into the download folder
    def download_videos_from_urls(self, urllist):
        self.dp = xbmcgui.DialogProgress()
        self.dp.create(translate(32000), translate(32019))

        # Get a dict of checksums (key=filename, value=checksum) if the setting is enabled
        if addon.getSettingBool("enable-checksums"):
            with open(os.path.join(addon_path, "resources", "checksums.json")) as f:
                checksums = f.read()
            checksums = json.loads(checksums)
        else:
            # If the setting was disabled, initialize an empty dict
            checksums = {}

        for url in urllist:
            if not self.stop:
                # Parse out the file name and construct its expected download location
                video_file = url.split("/")[-1]
                localfile = os.path.join(addon.getSetting("download-folder"), video_file)

                # If the file exists at the download location, get its checksum
                if xbmcvfs.exists(localfile):
                    if addon.getSettingBool("enable-checksums"):
                        with xbmcvfs.File(xbmcvfs.translatePath(localfile)) as f:
                            file_checksum = hashlib.md5(f.read()).hexdigest()

                        # If the computed checksum does not match the expected checksum, redownload
                        if video_file in checksums.keys() and checksums[video_file] != file_checksum:
                            self.download(localfile, url, video_file)
                    else:
                        self.download(localfile, url, video_file)
                else:
                    self.download(localfile, url, video_file)
            else:
                break

    def download(self, path, url, name):
        if xbmcvfs.exists(path):
            xbmcvfs.delete(path)

        self.dp.update(0, name)
        self.path = xbmc.translatePath(path)
        xbmc.sleep(500)
        start_time = time.time()

        u = urlopen(url)
        meta = u.info()
        meta_func = meta.getheaders if hasattr(meta, "getheaders") else meta.get_all
        meta_length = meta_func("Content-Length")
        file_size = None
        block_sz = 8192
        if meta_length:
            file_size = int(meta_length[0])

        file_size_dl = 0
        with xbmcvfs.File(self.path, 'wb') as f:
            numblocks = 0
            while not self.stop:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                f.write(buffer)
                file_size_dl += len(buffer)
                numblocks += 1
                self.dialogdown(name, numblocks, block_sz, file_size, self.dp, start_time)

    def dialogdown(self, name, numblocks, blocksize, filesize, dp, start_time):
        try:
            percent = int(min(numblocks * blocksize * 100 / filesize, 100))
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024)
            kbps_speed = numblocks * blocksize / (time.time() - start_time)
            if kbps_speed > 0:
                eta = (filesize - numblocks * blocksize) / kbps_speed
            else:
                eta = 0
            kbps_speed = kbps_speed / 1024
            total = float(filesize) / (1024 * 1024)
            mbs = '%.02f MB %s %.02f MB' % (currently_downloaded, translate(32015), total)
            e = ' (%.0f Kb/s) ' % kbps_speed
            tempo = translate(32016) + ' %02d:%02d' % divmod(eta, 60)
            dp.update(percent, f"{name} - {mbs}{e}\n{tempo}")
        except Exception:
            percent = 100
            dp.update(percent)

        if dp.iscanceled():
            self.stop = True
            dp.close()
            try:
                xbmcvfs.delete(self.path)
            except Exception:
                xbmc.log(msg='[Aerial ScreenSavers] Could not remove file', level=xbmc.LOGERROR)
            xbmc.log(msg='[Aerial ScreenSavers] Download canceled', level=xbmc.LOGDEBUG)
