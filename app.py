import json
import os.path
from requests import get
from concurrent.futures import ThreadPoolExecutor
import time
from urllib3.exceptions import InsecureRequestWarning
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
class Book:
    def __init__(self, config_file):
        with open(config_file, 'r', encoding='utf-8') as cf:
            config = json.load(cf)
        self.file = config["path"]
        self.workers = int(config["workers"])
        self.dedup = config["dedup"].lower() == "y"
        self.outpath = config["outpath"] if config["outpath"] else "./"
        self.type = self.recog_type(self.file)
        self.checked_books = 0
        self.success_books = 0
        self.books = self.json_to_books()

    def recog_type(self, file: str):
        if file.startswith('http'):
            return 'url'
        elif os.path.exists(file):
            return os.path.splitext(file)[1]
        else:
            return None

    def json_to_books(self):
        if self.type == '.json':
            with open(self.file, 'r', encoding='utf-8') as f:
                return json.load(f)

    def check(self, abook, timeout=3):
        headers = {
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Mobile Safari/537.36'
        }

        try:
            response = get(url=abook.get('bookSourceUrl'), verify=False, headers=headers, timeout=timeout)
            status = response.status_code

            if status == 200:
                return {'book': abook, 'status': True}
            else:
                return {'book': abook, 'status': False}

        except Exception as e:
            return {'book': abook, 'status': False}

    def checkbooks(self, workers=16):
        pool = ThreadPoolExecutor(workers)
        books = self.json_to_books()
        ans = list(pool.map(self.check, books))
        good = [item for item in ans if item['status']]
        error = [item for item in ans if not item['status']]
        return {"good": good, "error": error}


if __name__ == '__main__':
    print("欢迎使用书源校验工具（VerifyBookSource v3.0）\n")
    config_file = "path.json"  # 你的配置文件路径
    book_obj = Book(config_file)
    results = book_obj.checkbooks()
    good_results = results['good']
    error_results = results['error']

    # 这里将结果写入到json文件中
    with open(book_obj.outpath + 'good.json', 'w', encoding='utf-8') as f:
        json.dump([result['book'] for result in good_results], f, ensure_ascii=False)

    with open(book_obj.outpath + 'error.json', 'w', encoding='utf-8') as f:
        json.dump([result['book'] for result in error_results], f, ensure_ascii=False)

    print('\n有效的书源有：', len(good_results))
    print('无效的书源有：', len(error_results))
    print('有效的书源和无效的书源已分别写入' + book_obj.outpath + 'good.json和' + book_obj.outpath + 'error.json')
