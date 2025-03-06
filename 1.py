import os
import cloudscraper
from bs4 import BeautifulSoup
import re
import time
import logging
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename[:80])


def get_all_pages(base_url, scraper, cookies):
    """获取所有分页链接（改进版）"""
    all_pages = []
    parsed_base = urlparse(base_url)
    base_query = parse_qs(parsed_base.query)

    # 获取最大页码
    try:
        first_page = scraper.get(base_url, cookies=cookies)
        first_soup = BeautifulSoup(first_page.text, 'html.parser')
        ptt = first_soup.find('table', class_='ptt')
        max_page = int(ptt.find_all('td')[-2].text)  # 倒数第二个td是最大页码
    except:
        max_page = 1

    # 生成所有分页URL
    for p in range(0, max_page):
        new_query = base_query.copy()
        new_query['p'] = [str(p)]
        new_url = parsed_base._replace(query=urlencode(new_query, doseq=True))
        all_pages.append(urlunparse(new_url))

    return all_pages

def download_gallery(url, folder=r'D:\1'):
    # 必须配置的有效Cookie
    cookies = {
        "ipb_member_id": '',
        "ipb_pass_hash": "",
        "sk": "",  # 必须参数
    }

    # 创建会话
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'firefox', 'platform': 'windows', 'desktop': True},
        delay=15
    )

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Referer': 'https://e-hentai.org/'
    }

    try:
        # 处理年龄验证
        scraper.get("https://e-hentai.org/ageverify.php?redirect=" + url, cookies=cookies)

        # 获取所有分页
        all_pages = get_all_pages(url, scraper, cookies)
        logger.info(f"发现 {len(all_pages)} 个分页")

        # 收集所有图片链接
        all_links = []
        for page_url in all_pages:
            response = scraper.get(page_url, cookies=cookies, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 定位图片容器
            container = soup.find('div', {'id': 'gdt'})
            if container:
                for a in container.select('a[href^="https://e-hentai.org/s/"]'):
                    all_links.append(a['href'])
            time.sleep(1)

        logger.info(f"共发现 {len(all_links)} 张图片")

        # 获取标题（从第一页获取）
        response = scraper.get(url, cookies=cookies, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = sanitize_filename(soup.find('h1', id='gn').text.strip())
        logger.info(f'开始下载: {title}')

        # 创建文件夹
        save_path = os.path.join(folder, title)
        os.makedirs(save_path, exist_ok=True)

        # 遍历下载
        for idx, page_url in enumerate(all_links, 1):
            for retry in range(3):  # 重试机制
                try:
                    page = scraper.get(page_url, cookies=cookies, headers=headers)
                    page_soup = BeautifulSoup(page.text, 'html.parser')

                    # 定位图片
                    img_div = page_soup.find('div', {'id': 'i3'})
                    if img_div:
                        img_tag = img_div.find('img', {'id': 'img'}) or img_div.find('img')

                        if img_tag and (img_url := img_tag.get('src')):
                            # 处理URL格式
                            if img_url.startswith('//'):
                                img_url = f'https:{img_url}'
                            elif not img_url.startswith('http'):
                                img_url = f'https://{img_url}'

                            # 生成文件名
                            filename = f"{idx:03d}_{os.path.basename(img_url.split('?')[0])}"
                            filepath = os.path.join(save_path, filename)

                            if not os.path.exists(filepath):
                                logger.info(f'下载中 ({idx}/{len(all_links)})')
                                img_data = scraper.get(img_url, headers={
                                    'Referer': page_url,
                                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
                                }).content

                                with open(filepath, 'wb') as f:
                                    f.write(img_data)

                                time.sleep(2.5)
                            break
                except Exception as e:
                    if retry == 2:
                        logger.error(f'第 {idx} 张下载失败: {str(e)}')
                    time.sleep(5)

    except Exception as e:
        logger.error(f'致命错误: {str(e)}')


if __name__ == '__main__':
    download_gallery(input("请输入画廊URL："))