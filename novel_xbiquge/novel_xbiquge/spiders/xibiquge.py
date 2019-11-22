# -*- coding: utf-8 -*-
import scrapy
import pymysql
from copy import deepcopy
from ..items import NovelXbiqugeItem
from ..settings import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_CHARSET


class XibiqugeSpider(scrapy.Spider):
    name = 'xibiquge'
    allowed_domains = ['www.xbiquge.la']
    start_urls = ['http://www.xbiquge.la/xiaoshuodaquan/']

    def get_mysql_data(self, title, author):
        '''根据参数获取章节信息'''
        db = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DB,
                             charset=MYSQL_CHARSET)
        cursor = db.cursor()
        cursor.execute('SELECT chapter FROM novel WHERE title="{}" AND author="{}"'.format(title, author))
        return [i[0] for i in cursor.fetchall()]

    def parse(self, response):
        '''获取全部小说'''
        for ul in response.xpath('//*[@id="main"]/div/ul/li'):
            html_url = ul.xpath('./a/@href').extract_first().strip()
            yield scrapy.Request(url=html_url, callback=self.parse_novel, priority=1)

    def parse_novel(self, response):
        '''获取每一本小说下面的信息'''
        items = NovelXbiqugeItem()
        items['title'] = response.xpath('//*[@id="info"]/h1/text()').extract_first().strip()
        items['author'] = response.xpath('//*[@id="info"]/p[1]/text()').extract_first().strip().split('：')[-1].strip()
        chapters = self.get_mysql_data(items['title'], items['author'])
        for ordinal, a in enumerate(response.xpath('//*[@id="list"]/dl/dd/a'), 1):
            chapter_url = 'http://www.xbiquge.la' + a.xpath('./@href').extract_first().strip()
            items['chapter'] = a.xpath('./text()').extract_first().strip()
            items['ordinal'] = ordinal
            if items['chapter'] not in chapters:
                yield scrapy.Request(url=chapter_url, callback=self.parse_chapter, meta={'items': deepcopy(items)},
                                     dont_filter=True, priority=2)

    def parse_chapter(self, response):
        '''获取小说内容'''
        items = response.meta['items']
        dataList = response.xpath('//*[@id="content"]/text()').extract()
        if not dataList:
            dataList = response.xpath('//*[@id="content"]/*/text()').extract()
        L = []
        for data in dataList:
            data = data.strip()
            if data:
                if '手机站全新改版升级地址：http://m.xbiquge.la，数据和书签与电脑站同步，无广告清新阅读！' in data:
                    continue
                if '内容更新后，请重新刷新页面，即可获取最新更新！' in data:
                    continue
                L.append(data)
        content = '\r\n'.join(L).strip()
        if not content:  # 数据库中设置了不为空，这里为空程序会报错，从而查看不一样的地方
            items['content'] = None
        else:
            items['content'] = content
        yield items
