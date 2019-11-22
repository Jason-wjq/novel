# -*- coding: utf-8 -*-
import scrapy
import pymysql
from copy import deepcopy
from ..items import NovelHuanyueItem
from ..settings import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_CHARSET


class HuanyueSpider(scrapy.Spider):
    name = 'huanyue'
    allowed_domains = ['www.huanyue123.com']
    start_urls = ['http://www.huanyue123.com/book/quanbu/postdate-0-0-0-0-0-0-1.html']

    def get_mysql_data(self, title, author):
        '''根据title和author查找对应的章节名'''
        db = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DB,
                             charset=MYSQL_CHARSET)
        cursor = db.cursor()
        cursor.execute('SELECT chapter FROM novel WHERE title="{}" AND author="{}"'.format(title, author))
        return [i[0] for i in cursor.fetchall()]

    def parse(self, response):
        '''首页'''
        page = int(response.xpath('//*[@id="pagestats"]/text()').extract_first().split('/')[-1].strip())
        for a in response.xpath('//*[@id="main"]/div/div/div/dl'):
            html_url = a.xpath('./dd/h3/a/@href').extract_first().strip()
            items = NovelHuanyueItem()
            items['title'] = a.xpath('./dd/h3/a/text()').extract_first().strip()
            items['author'] = a.xpath('./dd[@class="book_other"]/span/text()').extract_first().strip()
            yield scrapy.Request(url=html_url, callback=self.parse_novel, meta={'items': deepcopy(items)}, priority=1)
        for n in range(2, page + 1):
            url = 'http://www.huanyue123.com/book/quanbu/postdate-0-0-0-0-0-0-{}.html'.format(n)
            yield scrapy.Request(url=url, callback=self.parse_page)

    def parse_page(self, response):
        '''分页中的操作'''
        for a in response.xpath('//*[@id="main"]/div/div/div/dl'):
            html_url = a.xpath('./dd/h3/a/@href').extract_first().strip()
            items = NovelHuanyueItem()
            items['title'] = a.xpath('./dd/h3/a/text()').extract_first().strip()
            items['author'] = a.xpath('./dd[@class="book_other"]/span/text()').extract_first().strip()
            yield scrapy.Request(url=html_url, callback=self.parse_novel, meta={'items': deepcopy(items)}, priority=1)

    def parse_novel(self, response):
        '''每一个小说操作'''
        items = response.meta['items']
        chapters = self.get_mysql_data(items['title'], items['author'])  # 获取章节
        for ordinal, a in enumerate(response.xpath('//*[@id="main"]/div/div/ul/li/a'), 1):
            chapter_url = a.xpath('./@href').extract_first().strip()
            chapter_name = a.xpath('./text()').extract_first().strip()
            items['ordinal'] = ordinal
            items['chapter'] = chapter_name
            if chapter_name not in chapters:  # 判断获取的章节名是否在数据库中，不在则获取
                yield scrapy.Request(url=chapter_url, callback=self.parse_chapter, meta={'items': deepcopy(items)},
                                     dont_filter=True, priority=2)

    def parse_chapter(self, response):
        '''对小说内容操作'''
        items = response.meta['items']
        dataList = response.xpath('//*[@id="htmlContent"]/text()').extract()
        L = []
        for data in dataList:
            data = data.strip()
            if data:
                L.append(data)
        content = '\r\n'.join(L).strip()
        if not content:  # 数据库中设置了不为空，这里为空程序会报错，从而查看不一样的地方
            items['content'] = None
        else:
            items['content'] = content.replace('幻月书院', '')
        yield items
