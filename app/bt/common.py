import asyncio
import re
from urllib import parse
from urllib.parse import unquote

import pyppeteer
import requests
import requests_html
from lxml import etree
from magic_google import MagicGoogle

import log
from app.message import Message


# def thunder_download1(url: str):
#     # 本地种子文件
#     if url.endswith(".torrent"):
#         os.system(r'"D:\programs\Thunder_11.2.2.1716v2_Green\Thunder\Program\Thunder.exe" {url}'.format(url=url))
#     else:
#         pythoncom.CoInitialize()  # 在多线程环境需要加这行代码
#         thunder = Dispatch('ThunderAgent.Agent64.1')
#         thunder.AddTask(url)
#         thunder.CommitTasks()
#         pythoncom.CoInitialize()
#
#     if url.endswith(".torrent") or url.startswith("magnet:") or url.startswith("thunder:"):
#         time.sleep(10)  # 让磁力链接有足够时间下载到种子
#
#         win = None
#         wins = pyautogui.getWindowsWithTitle("新建任务面板")
#         if len(wins) != 0:
#             win = wins[0]
#         win.activate()
#
#         print("screen size: [{0}, {1}]".format(pyautogui.size().width, pyautogui.size().height))
#         print("win size: ", win.size, "midbottom: ", win.midbottom)
#
#         # 从窗口的底部中间的位置开始，向上移动，移动一次，点击一直，这样一定可以点击到”立即下载”按钮
#         x = win.midbottom.x
#         y = win.midbottom.y
#         pyautogui.moveTo(x, y)
#         a = y - win.size.height / 2
#         while y > a:
#             y = y - 10
#             wins = pyautogui.getWindowsWithTitle("新建任务面板")
#             if len(wins) != 0:
#                 print("click position: ", x, y)
#                 pyautogui.click(x, y)
#             else:
#                 break


# def thunder_download(url: str):
#     # 本地种子文件
#     if url.endswith(".torrent"):
#         os.system(r'"C:\programs\Thunder_11.2.2.1716v2_Green\Thunder\Program\Thunder.exe" {url}'.format(url=url))
#     else:
#         try:
#             pythoncom.CoInitialize()
#             thunder = Dispatch('ThunderAgent.Agent64.1')
#             thunder.AddTask(url)
#             thunder.CommitTasks()
#             pythoncom.CoInitialize()
#         except Exception as e:
#             log.error("thunder_download exception: {}".format(e))
#
#     time.sleep(5)

def thunder_download(url: str):
    kubespider_url = "http://192.168.1.139:3080/api/v1/download"
    payload = {
        "dataSource": url,
        "path": ""
    }
    response = requests.post(kubespider_url, json=payload)

    if response.status_code == 200:
        print("发送下载请求到kubespider成功")
    else:
        print("发送下载请求到kubespider失败：", response.text)


def is_contain_key_word(s: str, key_word: str):
    key_words = re.split(r'[ ,+.\-_:：]', key_word)
    return key_words[0] in s


def deduplication(all_a):
    protocol = ""
    indexes = []
    for i in range(len(all_a)):
        a = all_a[i]
        if hasattr(a, "attrib"):
            url = a.attrib["href"]
        else:
            url = a.attrs["href"]

        if i == 0:
            fields = url.split(":")
            if len(fields) == 0:
                return
            protocol = fields[0]
        else:
            if not url.startswith(protocol):
                indexes.append(i)
    if indexes:
        log.info("要删除的索引下标：{0}".format(' '.join(map(str, indexes))))
    for idx in sorted(indexes, reverse=True):
        del all_a[idx]


class DownloadSite:
    def __init__(self, home_page, search_url=""):
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/90.0.4389.114 Safari/537.36 "
        }
        self.home_page = home_page
        self.search_url = search_url
        self.name2url = dict()
        self.sent_messages = set()

    def search(self, key_word: str, year: str):
        if key_word in self.name2url:
            return self.name2url[key_word]

        search_key_word = key_word + " " + year + " site:" + self.home_page

        print("search keyword: ", search_key_word)
        mg = MagicGoogle()
        for i in mg.search(query=search_key_word, num=1):
            # pprint.pprint(i)
            log.info("通过关键词\"{0}\"找到网页：{1}".format(key_word, i['url']))
            return i['url']
        return self.search_from_bing(key_word, year)

        # html = etree.HTML(requests.get(google_search_url, headers=self.headers).text)
        # url = html.xpath('//*[@id="rso"]/div[1]/div/div/div[1]/div/a/@href')
        # if url:
        #     log.info("通过关键词\"{0}\"找到网页：{1}".format(key_word, url))
        #     url = url[0]
        # else:
        #     log.info("will use bing")
        #     url = self.search_from_bing(key_word)
        # return url

    def search_from_bing(self, key_word: str, year: str):
        bing_search_url = "https://www.bing.com/search?q={0}".format(
            "{0} site:{1}".format(key_word + " " + year, self.home_page))
        html = etree.HTML(requests.get(bing_search_url, headers=self.headers).text)
        url = html.xpath("//*[@id='b_results']/li[1]/div[2]/div/cite")
        if url:
            log.info("找到《{0}》的网页：{1}".format(key_word, url))
            return url[0]
        else:
            log.info("error: can't find url")
            return ""

    def get_download_url_all(self, url, media_name):
        try:
            download_urls = self.get_download_url_use_r(url, media_name)
            if download_urls:
                return download_urls
            log.info("使用requests-html获取下载链接")
            return self.get_download_url_use_rhtml(url, media_name)
        except Exception as e:
            log.error("catch exception: {0}".format(str(e)))

    def get_download_url_use_rhtml(self, url, media_name):
        async def load_page_helper(url: str):
            """Helper to parse obfuscated / JS-loaded profiles like Facebook.
            We need a separate function to handle requests-html's async nature
            in Django's event loop."""
            session = requests_html.AsyncHTMLSession()
            browser = await pyppeteer.launch({
                'ignoreHTTPSErrors': True,
                'headless': True,
                'handleSIGINT': False,
                'handleSIGTERM': False,
                'handleSIGHUP': False
            })
            session._browser = browser

            resp = await session.get(url)
            await resp.html.arender(timeout=60)
            await session.close()
            await browser.close()
            return resp

        r = asyncio.run(load_page_helper(url))

        # r = asession.run(get_html)[0]

        # r = asession.get(url)
        # await r.html.arender(timeout=60)
        all_a = r.html.xpath(
            "//*[starts-with(@href, 'magnet:') or starts-with(@href, 'thunder:') or starts-with(@href, 'ed2k:')]")
        deduplication(all_a)
        download_urls = dict()
        for a in all_a:
            url = a.attrs["href"]
            if a.encoding != "utf-8":
                url = url.encode(a.encoding, errors='ignore').decode("utf-8", errors='ignore')
            url_decode = unquote(url)
            if "title" in a.attrs and is_contain_key_word(a.attrs["title"], media_name) and "粤语" not in a.attrs["title"]:
                name = a.attrs["title"]
            elif is_contain_key_word(url_decode, media_name) and "粤语" not in url_decode:
                params = parse.parse_qs(parse.urlparse(url_decode).query)
                name = params["dn"][0]
            else:
                continue

            url = url.replace("\r", "")
            download_urls[name] = url
            log.info("site: {0}, name: {1}, url: {2}".format(self.home_page, name, url))

        return download_urls

    def get_download_url_use_r(self, url, media_name):
        resp = requests.get(url, headers=self.headers)

        if resp.encoding == 'ISO-8859-1':
            encodings = requests.utils.get_encodings_from_content(resp.text)
            if encodings:
                resp.encoding = encodings[0]
            else:
                resp.encoding = resp.apparent_encoding

        tree = etree.HTML(resp.text)
        all_a = tree.xpath(
            "//*[starts-with(@href, 'magnet:') or starts-with(@href, 'thunder:') or starts-with(@href, 'ed2k:')]")
        deduplication(all_a)
        download_urls = dict()
        for a in all_a:
            url = a.attrib["href"]
            url_decode = unquote(url)
            if "title" in a.attrib and is_contain_key_word(a.attrib["title"], media_name) and "粤语" not in a.attrib["title"]:
                name = a.attrib["title"]
            elif is_contain_key_word(url_decode, media_name) and "粤语" not in url_decode:
                params = parse.parse_qs(parse.urlparse(url_decode).query)
                name = params["dn"][0]
            elif "ed2k://|file|" in url:
                name = url.split("|")[2]
            else:
                continue

            url = url.replace("\r", "")
            download_urls[name] = url
            log.info("site: {0}, name: {1}, url: {2}".format(self.home_page, name, url))

        return download_urls

    def download(self, media_name: str, year: str, episodes: list[int] = None, image: str = None):
        n = 0

        if episodes:
            is_tv = True
        else:
            is_tv = False

        url = self.search(media_name, year)
        if not url:
            log.error("【BT】查找url失败，key_word: {0}, year: {1}".format(media_name, year))
            return n
        else:
            log.info("获取到url：{}, 关键字：{}, year: {}".format(url, media_name, year))

        durls = self.get_download_url_all(url, media_name)
        if not durls:
            log.error("【BT】在网页[{0}]查找下载链接失败，key_word: {1}".format(url, media_name))
            return n
        else:
            self.name2url[media_name] = url

        for name, url in sorted(durls.items()):
            if is_tv:
                m = re.search(r"第(\d+)集", name)
                if not m:
                    m = re.search(r"EP?(\d+).*", name)

                if not m:
                    log.error("没有识别到集数：{0}".format(name))
                    continue

                ep = int(m.group(1))

                if ep in episodes:
                    log.info("开始下载{0}第{1}集：{2}".format(media_name, ep, url))
                    if f'{media_name}EP{ep}开始迅雷下载' not in self.sent_messages:
                        self.sent_messages.add(f'{media_name}EP{ep}开始迅雷下载')
                        Message().send_custom_message(clients=['1'], title=f'{media_name}EP{ep}开始迅雷下载', text='',
                                                      image=image)
                    thunder_download(url)
                    n = n + 1
            else:
                log.info("开始下载{0}：{1}".format(media_name, url))
                if f'{media_name}开始迅雷下载' not in self.sent_messages:
                    self.sent_messages.add(f'{media_name}开始迅雷下载')
                    Message().send_custom_message(clients=['1'], title=f'{media_name}开始迅雷下载', text='',
                                                  image=image)
                thunder_download(url)
                n = n + 1

        return n


if __name__ == "__main__":
    # thunder_download(
    #    "magnet:?xt=urn:btih:099b9a1151be63f264d23b0e78335fb12e22709f&dn=[www.mp4kan.com]%E8%84%90%E5%B8%A6.2022.HD1080p.%E4%B8%AD%E8%8B%B1%E5%8F%8C%E5%AD%97.mp4&tr=https://tracker.iriseden.fr:443/announce&tr=https://tr.highstar.shop:443/announce&tr=https://tr.fuckbitcoin.xyz:443/announce&tr=https://tr.doogh.club:443/announce&tr=https://tr.burnabyhighstar.com:443/announce&tr=https://t.btcland.xyz:443/announce&tr=http://vps02.net.orel.ru:80/announce&tr=https://tracker.kuroy.me:443/announce&tr=http://tr.cili001.com:8070/announce&tr=http://t.overflow.biz:6969/announce&tr=http://t.nyaatracker.com:80/announce&tr=http://open.acgnxtracker.com:80/announce&tr=http://nyaa.tracker.wf:7777/announce&tr=http://home.yxgz.vip:6969/announce&tr=http://buny.uk:6969/announce&tr=https://tracker.tamersunion.org:443/announce&tr=https://tracker.nanoha.org:443/announce&tr=https://tracker.loligirl.cn:443/announce&tr=udp://bubu.mapfactor.com:6969/announce&tr=http://share.camoe.cn:8080/announce&tr=udp://movies.zsw.ca:6969/announce&tr=udp://ipv4.tracker.harry.lu:80/announce&tr=udp://tracker.sylphix.com:6969/announce&tr=http://95.216.22.207:9001/announce")
    # thunder_download(
    #    "D:/迅雷下载/1F6DD43DEBA00DB2795E74A9E91620EF8142A776.torrent")

    site = DownloadSite("https://www.bdys03.com", "https://www.bdys03.com/search/{key_word}")
    tv_name = "云襄传"
    site.download(tv_name, '2023', [3, 4])
