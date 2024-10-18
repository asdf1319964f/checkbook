import json
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import urllib3
from tqdm import tqdm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Book:
    def __init__(self, config_file):
        with open(config_file, 'r', encoding='utf-8') as cf:
            config = json.load(cf)
        self.file = config.get("path")
        self.workers = int(config.get("workers", 5))
        self.dedup = config.get("dedup", "n").lower() == "y"
        self.outpath = config.get("outpath") or "./"
        self.type = self.recog_type(self.file)
        self.books = self.json_to_books()

    def recog_type(self, file: str):
        if file.startswith('http'):
            return 'url'
        elif os.path.exists(file):
            return os.path.splitext(file)[1]
        return None

    def json_to_books(self):
        if self.type == '.json':
            with open(self.file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    @staticmethod
    def check(abook, timeout=3):
        headers = {
            'user-agent': (
                'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 '
                'Mobile Safari/537.36'
            )
        }
        try:
            response = requests.get(url=abook['bookSourceUrl'], verify=False, headers=headers, timeout=timeout)
            return {'book': abook, 'status': response.status_code == 200}
        except requests.RequestException:
            return {'book': abook, 'status': False}

    def checkbooks(self):
        good, error = [], self.books
        max_attempts = 5
        attempts = 0

        while error and attempts < max_attempts:
            new_good, new_error = [], []
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = [executor.submit(self.check, book) for book in error]
                for future in tqdm(as_completed(futures), total=len(error), desc="检 查 进 度 "):
                    result = future.result()
                    (new_good if result['status'] else new_error).append(result)
                    print(f"\r成 功 : {len(good) + len(new_good)} | 失 败 : {len(new_error)}", end="", flush=True)

            good.extend(new_good)
            error = [result['book'] for result in new_error]
            attempts += 1  # 增加尝试次数

        print()  # 换行
        return {"good": good, "error": error}

def main():
    print("欢 迎 使 用 书 源 校 验 工 具 （ VerifyBookSource v3.0） \n")
    config_file = "path.json"  # 配置文件路径
    book_obj = Book(config_file)
    start_time = time.time()
    results = book_obj.checkbooks()
    end_time = time.time()

    os.makedirs(book_obj.outpath, exist_ok=True)
    with open(os.path.join(book_obj.outpath, 'good.json'), 'w', encoding='utf-8') as f:
        json.dump([result['book'] for result in results['good']], f, ensure_ascii=False, indent=2)
    with open(os.path.join(book_obj.outpath, 'error.json'), 'w', encoding='utf-8') as f:
        json.dump([result['book'] for result in results['error']], f, ensure_ascii=False, indent=2)

    print(f'\n检 查 完 成 ， 耗 时  {end_time - start_time:.2f} 秒 ')
    print(f'有 效 的 书 源 ： {len(results["good"])}')
    print(f'无 效 的 书 源 ： {len(results["error"])}')
    print(f'有 效 的 书 源 和 无 效 的 书 源 已 分 别 写 入  {book_obj.outpath}good.json 和  {book_obj.outpath}error.json')

if __name__ == '__main__':
    main()
