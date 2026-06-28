"""
千里马标讯平台爬虫 - 使用 Playwright (ARM64兼容)
"""
import base64
import time
import json
import ddddocr
import requests
import logging
import os
import glob
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from crawlers.base_crawler import BaseCrawler, BidInfo

logger = logging.getLogger(__name__)


class QianliMaCrawler(BaseCrawler):
    """千里马标讯平台爬虫 - Playwright方式"""

    name = "qianlima"
    description = "千里马标讯平台爬虫"

    BASE_URL = "https://cusdatavip.qianlima.com"

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': self.BASE_URL,
            'Referer': f'{self.BASE_URL}/'
        })
        self.ocr = ddddocr.DdddOcr()
        self.browser = None
        self.page = None
        self.playwright = None

    def _init_driver(self):
        """初始化Playwright浏览器"""
        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()

            # 使用 Chromium (ARM64 原生支持)
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )

            self.page = self.browser.new_page()
            self.page.set_viewport_size({"width": 1920, "height": 1080})

            logger.info("Playwright浏览器初始化成功")
            return True
        except Exception as e:
            logger.error(f"初始化浏览器失败: {e}")
            return False

    def login(self, credentials: Dict[str, str]) -> bool:
        """登录千里马平台"""
        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            logger.error("缺少用户名或密码")
            return False

        if not self._init_driver():
            return False

        max_retry = 3
        for attempt in range(max_retry):
            logger.info(f"登录尝试 {attempt + 1}/{max_retry}")

            try:
                # 访问登录页面
                self.page.goto(f"{self.BASE_URL}/login.html", wait_until="networkidle")
                time.sleep(2)

                # 获取验证码图片
                img_element = self.page.wait_for_selector("#img", timeout=10000)
                img_src = img_element.get_attribute("src")

                if img_src and "base64" in img_src:
                    img_b64 = img_src.split(",")[1]
                    img_bytes = base64.b64decode(img_b64)
                    captcha_text = self.ocr.classification(img_bytes)
                    logger.info(f"验证码识别: {captcha_text}")

                    # 填写表单
                    self.page.fill("#keuUpName", username)
                    self.page.fill("#keuUpPwd", password)
                    self.page.fill("input[name='verificationCode']", captcha_text)

                    # 点击登录
                    self.page.click(".logInBtn")

                    time.sleep(4)

                    # 检查登录结果
                    current_url = self.page.url
                    page_content = self.page.content()

                    if "index" in current_url or "退出" in page_content:
                        logger.info("登录成功")
                        self.logged_in = True

                        # 同步cookies到requests session
                        cookies = self.page.context.cookies()
                        for cookie in cookies:
                            self.session.cookies.set(
                                cookie['name'],
                                cookie['value'],
                                domain=cookie.get('domain', ''),
                                path=cookie.get('path', '/')
                            )
                        logger.info(f"已同步 {len(cookies)} 个cookie")

                        return True
                    else:
                        # 检查TOKEN cookie
                        cookies = self.page.context.cookies()
                        for cookie in cookies:
                            if cookie['name'] == 'TOKEN' and len(cookie['value']) > 20:
                                logger.info("检测到TOKEN cookie，登录成功")
                                self.logged_in = True

                                for c in cookies:
                                    self.session.cookies.set(
                                        c['name'],
                                        c['value'],
                                        domain=c.get('domain', ''),
                                        path=c.get('path', '/')
                                    )

                                logger.info(f"已同步 {len(cookies)} 个cookie")
                                return True

                        logger.warning(f"登录失败，当前URL: {current_url}")
                        # 刷新验证码重试
                        try:
                            self.page.click("#img")
                            time.sleep(1)
                        except:
                            pass

            except Exception as e:
                logger.error(f"登录异常: {e}")

        return False

    def search(self, params) -> List[BidInfo]:
        """搜索标讯"""
        if not self.logged_in:
            logger.error("未登录")
            return []

        try:
            if isinstance(params, dict):
                region_codes = params.get("region_codes", [])
                start_date = params.get("start_date", "")
                end_date = params.get("end_date", "")
            else:
                region_codes = params.region_codes
                start_date = params.start_date
                end_date = params.end_date

            if not start_date or not end_date:
                today = datetime.now()
                week_ago = today - timedelta(days=7)
                start_date = week_ago.strftime('%Y-%m-%d')
                end_date = today.strftime('%Y-%m-%d')

            logger.info(f"搜索参数: 地区={region_codes}, 时间={start_date} ~ {end_date}")

            # 导航到搜索页面
            self.page.goto(f"{self.BASE_URL}/search.html", wait_until="networkidle")
            time.sleep(3)

            # 选择招标数据类型
            try:
                self.page.click("li[data-id='229']")
                logger.info("已选择招标数据")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"选择招标数据失败: {e}")

            # 选择地区
            self._select_regions(region_codes)

            # 设置时间范围
            self._set_date_range(start_date, end_date)

            # 点击搜索
            self._click_search()

            # 等待搜索结果
            time.sleep(5)

            # 导出数据
            bids = self._export_data()

            return bids

        except Exception as e:
            logger.error(f"搜索异常: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _select_regions(self, region_codes: List[str]):
        """选择地区"""
        region_map = {
            "500000": "重庆市",
            "510000": "四川省",
            "530000": "云南省",
            "520000": "贵州省",
            "540000": "西藏自治区"
        }

        try:
            # 点击地区选择框
            self.page.click("div.mucaser-result.form-control .mcr-result")
            time.sleep(1)

            # 选择各省份
            for code in region_codes:
                try:
                    self.page.click(f"div.mucaser-list-item[data-id-arr='{code}'] .mucaser-list-item-label")
                    logger.info(f"已选择 {region_map.get(code, code)}")
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"选择地区 {code} 失败: {e}")

            time.sleep(1)

        except Exception as e:
            logger.warning(f"选择地区失败: {e}")

    def _set_date_range(self, start_date: str, end_date: str):
        """设置时间范围"""
        try:
            # 直接设置输入框的值
            start_input = self.page.query_selector("input#startTime")
            end_input = self.page.query_selector("input#endTime")

            if start_input and end_input:
                start_input.fill(start_date)
                end_input.fill(end_date)
                logger.info(f"已设置时间范围: {start_date} ~ {end_date}")

            time.sleep(1)

        except Exception as e:
            logger.warning(f"设置时间范围失败: {e}")

    def _click_search(self):
        """点击搜索按钮"""
        try:
            self.page.click("label[for='submit'].btn")
            logger.info("正在搜索...")
            time.sleep(5)
        except Exception as e:
            logger.warning(f"点击搜索按钮失败: {e}")
            try:
                self.page.evaluate("document.querySelector('input#submit').click();")
                time.sleep(5)
            except:
                pass

    def _export_data(self) -> List[BidInfo]:
        """导出数据"""
        download_dir = os.environ.get("DOWNLOAD_DIR", "/tmp/downloads")
        os.makedirs(download_dir, exist_ok=True)

        # 清理旧的千里马数据文件
        old_files = glob.glob(os.path.join(download_dir, "千里马数据表*.xlsx"))
        for f in old_files:
            try:
                os.remove(f)
                logger.info(f"删除旧文件: {f}")
            except:
                pass

        try:
            time.sleep(3)

            # 检查搜索结果数量
            try:
                result_text = self.page.locator('.result-count, .total-count, #totalCount').first.text_content(timeout=5000)
                logger.info(f"搜索结果数量: {result_text}")
            except Exception as e:
                logger.warning(f"无法获取结果数量: {e}")

            # 使用 expect_download 处理下载
            try:
                with self.page.expect_download(timeout=90000) as download_info:
                    self.page.click("a#export", timeout=10000)
                    logger.info("已点击导出按钮，等待下载...")

                download = download_info.value
                filename = download.suggested_filename
                logger.info(f"下载文件名: {filename}")
                download_path = os.path.join(download_dir, filename)
                download.save_as(download_path)
                logger.info(f"下载保存到: {download_path}")
                return self._parse_excel(download_path)

            except Exception as e:
                logger.error(f"下载失败: {e}")

                # 备用方案：检查下载目录
                logger.info("检查下载目录中的文件...")
                time.sleep(3)

                all_files = glob.glob(os.path.join(download_dir, "千里马数据表*.xlsx"))
                if all_files:
                    newest_file = max(all_files, key=os.path.getctime)
                    if os.path.getsize(newest_file) > 0:
                        logger.info(f"找到下载文件: {newest_file}")
                        return self._parse_excel(newest_file)

                logger.warning("未找到下载的Excel文件")
                return []

        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_excel(self, file_path: str) -> List[BidInfo]:
        """解析Excel文件"""
        try:
            import pandas as pd
            import math

            df = pd.read_excel(file_path, engine='openpyxl')
            logger.info(f"读取到 {len(df)} 条记录")

            def safe_str(val):
                if pd.isna(val) or (isinstance(val, float) and math.isnan(val)):
                    return ''
                return str(val)

            bids = []
            for _, row in df.iterrows():
                try:
                    raw_data = {k: safe_str(v) for k, v in row.to_dict().items()}
                    province = raw_data.get('省', '') or raw_data.get('province', '')
                    city = raw_data.get('市', '') or raw_data.get('city', '')
                    region = province + city if province else ''

                    bid = BidInfo(
                        id=safe_str(row.iloc[0]) if len(row) > 0 else '',
                        title=safe_str(row.iloc[4]) if len(row) > 4 else '',
                        tender_unit=safe_str(row.iloc[9]) if len(row) > 9 else '',
                        crm_industry=safe_str(row.iloc[14]) if len(row) > 14 else '',
                        budget=safe_str(row.iloc[19]) if len(row) > 19 else '',
                        region=region,
                        publish_date=raw_data.get('发布时间', '') or safe_str(row.iloc[43]) if len(row) > 43 else '',
                        deadline=raw_data.get('投标截止时间', '') or safe_str(row.iloc[41]) if len(row) > 41 else '',
                        open_date=raw_data.get('开标时间', ''),
                        source='qianlima',
                        link=raw_data.get('URL', '') or safe_str(row.iloc[29]) if len(row) > 29 else '',
                        raw_data=raw_data
                    )
                    if bid.title:
                        bids.append(bid)
                except Exception as e:
                    continue

            logger.info(f"解析完成，共 {len(bids)} 条有效标讯")
            return bids

        except Exception as e:
            logger.error(f"解析Excel失败: {e}")
            return []

    def get_detail(self, bid_id: str) -> Optional[BidInfo]:
        """获取标讯详情"""
        return None

    def close(self):
        """关闭浏览器"""
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
            self.browser = None
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
            self.playwright = None