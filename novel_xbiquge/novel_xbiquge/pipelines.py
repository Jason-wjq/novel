# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import hashlib
import os
import pymysql
from twisted.enterprise import adbapi


def MD5(md5List: list):
    # 生成一个md5对象
    m1 = hashlib.md5()
    for value in md5List:
        if (value is not None) and (not isinstance(value, bool)):
            # 使用md5对象里的update方法md5转换
            m1.update(str(value).encode("utf-8"))
    token = m1.hexdigest()
    return token


class NovelXbiqugePipeline(object):
    '''使用异步的形式入库'''

    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.path = r'D:\library'  # 保存路径

    @classmethod
    def from_settings(cls, settings):  # 固定格式
        params = dict(
            host=settings['MYSQL_HOST'],
            db=settings['MYSQL_DB'],
            user=settings['MYSQL_USER'],
            passwd=settings['MYSQL_PASSWORD'],
            charset=settings['MYSQL_CHARSET'],
            cursorclass=pymysql.cursors.DictCursor
        )
        db_connect_pool = adbapi.ConnectionPool('pymysql', **params)
        return cls(db_connect_pool)  # 初始化

    def process_item(self, item, spider):
        title = item['title']
        author = item['author']
        chapter = item['chapter']
        content = item['content']
        ordinal = item['ordinal']
        id = MD5([title, author, chapter, content, ordinal])
        content_path = os.path.join(self.path, id)
        with open(content_path, 'w', encoding='utf-8') as f:  # 把内容保存在本地，数据库中保存地址
            f.write(content)
        result = self.db_pool.runInteraction(self.insert, (id, title, author, chapter, content_path, ordinal))
        result.addErrback(self.error)  # 给result绑定一个回调函数，用于监听错误信息

    def error(self, reason):
        print('--------', reason)

    def insert(self, cursor, data):
        insert_sql = 'REPLACE INTO novel(id,title,author,chapter,content_path,ordinal) VALUES (%s,%s,%s,%s,%s,%s)'
        cursor.execute(insert_sql, data)
