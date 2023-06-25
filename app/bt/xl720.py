from app.bt.common import *


class XL720(DownloadSite):
    def __init__(self, url, search_url):
        super().__init__(url, search_url)

    def search(self, key_word, year):
        if key_word in self.name2url:
            return self.name2url[key_word]

        url = self.search_url.replace("{key_word}", key_word + " " + year)
        log.info("使用关键词[{0}]进行搜索：{1}".format(key_word, url))
        # get请求，传入参数，返回结果集
        resp = requests.get(url, headers=self.headers)
        # 将结果集的文本转化为树的结构
        tree = etree.HTML(resp.text)
        lists = tree.xpath("//*[@id='content']/div[2]/div[@class='post clearfix']/h3/a")
        for l in lists:
            for element in l.iter():
                if len(element.attrib.keys()) != 0:
                    log.info("搜索结果：{0}".format(element.attrib))

        if len(lists) > 0:
            self.name2url[key_word] = lists[0].attrib["href"]
            return lists[0].attrib["href"]
        else:
            return super().search(key_word, year)

    def get_download_url_all(self, url, media_name):
        log.info(url)
        resp = requests.get(url, headers=self.headers)
        tree = etree.HTML(resp.text)
        titles = tree.xpath("//*[@id='zdownload']/div[1]/a/@title")
        links = tree.xpath("//*[@id='zdownload']/div[1]/a/@href")

        media_type = tree.xpath("//*[@class='meta-author']/a[1]/text()")[0]
        log.info("media_type: {0}".format(media_type))

        download_urls = dict()
        if "电视剧" in media_type:
            for i in range(len(titles)):
                if "粤语" not in titles[i]:
                    log.info("name: {0}, url: {1}".format(titles[i], links[i]))
                    download_urls[titles[i]] = links[i]
        else:
            log.info("name: {0}, url: {1}".format(titles[0], links[0]))
            download_urls[titles[0]] = links[0]

        return download_urls


if __name__ == "__main__":
    sites = [  # DownloadSite("https://www.dbmp4.com"),
        # XL720("https://www.xl720.com", "https://www.xl720.com/?s={key_word}"),
        # DownloadSite("https://www.btdx8.com", "https://www.btdx8.com/?s={key_word}"),
        DownloadSite("https://www.dy2018.com"),
        # DownloadSite("https://www.ciligod.com/movie")
    ]
    media_name = "梦华录"
    for site in sites:
        log.info("web site: {0}".format(site.home_page))
        site.get_download_url(site.search(media_name, "2022"), media_name)
