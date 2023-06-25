import logging
import threading

from app.bt.common import *
from app.bt.xl720 import XL720


class TVWatcher(threading.Thread):
    def __init__(self, download_sites: list[DownloadSite], tv_names=None, interval: int = 1800):
        super().__init__()
        if tv_names is None:
            tv_names = []
        self.tv_name2url = dict()
        self.download_sites = download_sites
        self.tv_names = tv_names
        self.interval = interval
        self.tv_name2durls = dict()

        for site in self.download_sites:
            for name in tv_names:
                self.tv_name2durls[self.get_key(name, site)] = self.get_download_url(name, site)

    def run(self) -> None:
        while True:
            time.sleep(self.interval)
            logging.info("TVWatcher::run()")
            self.download_update()

    def start(self) -> None:
        logging.info("TVWatcher start")
        super().start()

    def add_tv(self, name):
        self.tv_names.append(name)
        for site in self.download_sites:
            self.tv_name2durls[self.get_key(name, site)] = self.get_download_url(name, site)

    def get_key(self, name: str, site: DownloadSite):
        return site.home_page + "_" + name

    def get_download_url(self, name: str, download_site: DownloadSite):
        if self.get_key(name, download_site) not in self.tv_name2url:
            tv_url = download_site.search(name)
            if tv_url == "":
                logging.info("获取电视[{0}]在网站[{1}]的网页失败".format(name, download_site.home_page))
                return
            self.tv_name2url[self.get_key(name, download_site)] = tv_url
        tv_url = self.tv_name2url[self.get_key(name, download_site)]

        download_urls = download_site.get_download_url(tv_url, name)
        if not download_urls:
            logging.info("获取电视[{0}]在网页{1}的下载链接失败".format(name, tv_url))
            return

        return download_urls

    def download_update(self):
        for site in self.download_sites:
            for name in self.tv_names:
                try:
                    new_durls = self.get_download_url(name, site)
                    old_durls = self.tv_name2durls[self.get_key(name, site)]
                    for k, v in new_durls.items():
                        if k not in old_durls:
                            logging.info("下载{0}使用链接：{1}".format(k, v))
                            thunder_download(v)
                    self.tv_name2durls[self.get_key(name, site)] = new_durls
                except Exception as e:
                    logging.exception("catch exception：{0}".format(str(e)))
                    continue


sites = [DownloadSite("https://www.dbmp4.com"),
         XL720("https://www.xl720.com", "https://www.xl720.com/?s={key_word}"),
         DownloadSite("https://www.btdx8.com", "https://www.btdx8.com/?s={key_word}"),
         DownloadSite("https://www.dy2018.com"),
         # DownloadSite("https://www.ciligod.com/movie")
         ]
tv_watcher = TVWatcher(sites)

if __name__ == "__main__":

    Log_Format = "%(asctime)s - %(levelname)s - %(filename)s[:%(lineno)d] - %(message)s"
    logging.basicConfig(filename="logfile.log",
                        filemode="w",
                        format=Log_Format,
                        level=logging.INFO)
    logger = logging

    sites = [DownloadSite("https://www.dbmp4.com"),
             XL720("https://www.xl720.com", "https://www.xl720.com/?s={key_word}"),
             DownloadSite("https://www.btdx8.com", "https://www.btdx8.com/?s={key_word}"),
             # DownloadSite("https://www.dy2018.com"),
             # DownloadSite("https://www.ciligod.com/movie")
             ]
    tv_name = "白色强人2"
    tv_watchers = [TVWatcher(sites, [tv_name])]

    for watcher in tv_watchers:
        time.sleep(600)
        watcher.download_update()
