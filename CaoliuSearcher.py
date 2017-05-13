import requests
from bs4 import BeautifulSoup
import argparse
import sqlite3
from urllib import parse
import time
from random import randint


class Searcher(object):
    def __init__(self):
        self.headers = {
                'Host': 't66y.com',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age = 0',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari / 537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, sdch',
                'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6'
        }
        self.max_page = -1

        self.conn = None
        self.cursor = None

    def search(self, fid, db_name, type=None, search=None, is_clean_table=False):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute('create table if not exists fid{} (title varchar(200), url varchar(100))'.format(fid))
        if is_clean_table:
            self.cursor.execute('delete from fid{}'.format(fid))

        params = {'fid': fid}
        if type:
            params['type'] = type
        if search:
            params['search'] = search
        self.fetch(params, 1)

    def fetch(self, params, page):
        print('Fetching page {}'.format(str(page)))
        params['page'] = str(page)

        try:
            r = requests.get('http://t66y.com/thread0806.php', params=params, headers=self.headers, timeout=15)
            r.encoding = 'gbk'
            r.raise_for_status()
        except requests.exceptions.Timeout as e:
            print(e)
        except requests.exceptions.RequestException as e:
            print(e)
        else:
            soup = BeautifulSoup(r.text)
            main = soup.body.find('div', id='main')

            # 先查一次总共有多少页
            if page == 1 and self.max_page == -1:
                a_page = main.find_all('table', recursive=False)[1].tr.td.div.find('a', id='last')
                parse_result = parse.urlparse(a_page['href'])
                url_param = parse.parse_qs(parse_result.query)
                self.max_page = int(url_param['page'][0])

            # 解析需要存数据库的内容
            content = main.find_all('div', class_='t', recursive=False)[1].table.tbody.find_all('tr', class_='tr3 t_one tac', recursive=False)
            for tr in content:
                td = tr.find('td', class_='tal')
                if td and td.find('h3'):
                    h3 = td.h3
                    if h3 and h3.find('a'):
                        a = h3.a
                        if not a['href'].startswith('read.php'):  # 论坛公告
                            url = 'http://t66y.com/' + a['href']
                            self.cursor.execute('insert into fid{} (title, url) values(\'{}\', \'{}\')'.format(params['fid'], a.string, url))

            if page < self.max_page:
                random_delay()
                self.fetch(params, page + 1)
            else:
                self.cursor.close()
                self.conn.commit()
                self.conn.close()


def random_delay():
    time.sleep(randint(1, 3))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Caoliu Searcher')
    parser.add_argument('--fid', dest='fid', required=True)
    parser.add_argument('--type', dest='type')
    parser.add_argument('--search', dest='search')
    parser.add_argument('--db', dest='db_name', required=True)
    parser.add_argument('--clean', dest='clean_table', action='store_true')

    args = parser.parse_args()

    s = Searcher()
    s.search(args.fid, args.db_name, args.type, args.search, args.clean_table)
