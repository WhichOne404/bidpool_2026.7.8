#!/usr/bin/env python
"""
测试千里马爬虫
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlers.qianlima import QianliMaCrawler
from datetime import datetime, timedelta

def test_crawler():
    """测试爬虫"""
    print("=" * 60)
    print("千里马爬虫测试")
    print("=" * 60)

    # 配置
    credentials = {
        "username": "chaitin04",
        "password": "chaitin04"
    }

    # 时间范围：最近7天
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    start_date = week_ago.strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')

    # 地区：重庆
    region_codes = ["500000"]

    print(f"\n时间范围: {start_date} ~ {end_date}")
    print(f"地区代码: {region_codes}")
    print(f"账号: {credentials['username']}")

    # 初始化爬虫
    crawler = QianliMaCrawler()

    try:
        # 1. 登录
        print("\n[1/2] 登录中...")
        if not crawler.login(credentials):
            print("登录失败!")
            return

        # 2. 搜索
        print("\n[2/2] 搜索标讯...")
        bids = crawler.search({
            "region_codes": region_codes,
            "start_date": start_date,
            "end_date": end_date
        })

        # 3. 输出结果
        print(f"\n找到 {len(bids)} 条标讯:")
        print("-" * 60)
        for i, bid in enumerate(bids[:10], 1):
            print(f"\n{i}. {bid.title}")
            print(f"   招标单位: {bid.tender_unit}")
            print(f"   行业: {bid.crm_industry}")
            print(f"   预算: {bid.budget}")
            print(f"   发布日期: {bid.publish_date}")
            print(f"   链接: {bid.link}")

        if len(bids) > 10:
            print(f"\n... 还有 {len(bids) - 10} 条")

        print("\n" + "=" * 60)
        print("测试完成!")

    finally:
        crawler.close()


if __name__ == "__main__":
    test_crawler()
