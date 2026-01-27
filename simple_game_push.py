# 简化版游戏数据推送到微信公众号
import os
import requests
import json
import curl_cffi.requests
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 微信公众号配置 - 可以直接填写或使用环境变量
appID = os.environ.get("APP_ID", "wx06948af05ffacf02")
appSecret = os.environ.get("APP_SECRET", "68942a7b76350d5c9bcd9b3cfc57e0bd")
openId = os.environ.get("OPEN_ID", "owzvx2FPYTAZGfb_os0AoZkd4UeY")
template_id = os.environ.get("TEMPLATE_ID", "yiNc0QFCcdBsKuJ48CATDOEg-3k0XD9gWAlQX9dQJSw")

def test_proxy_and_fetch(proxy, url, headers):
    """
    测试单个代理并尝试获取数据
    """
    try:
        # 处理不同格式的代理
        if not proxy or not (proxy.startswith('socks5://') or proxy.startswith('socks4://') or 
                            proxy.startswith('http://') or proxy.startswith('https://')):
            return None
        
        proxies = {'http': proxy, 'https': proxy}
        
        response = curl_cffi.requests.get(
            url, 
            headers=headers,
            proxies=proxies,
            impersonate="chrome120", 
            timeout=5  # 缩短超时时间到5秒
        )
        
        if response.status_code == 200:
            json_data = response.json()
            
            # 提取游戏数据
            if "data" in json_data and "results" in json_data["data"]:
                results = json_data["data"]["results"]
                game_data = []
                
                for result in results:
                    game_name = result.get("game", {}).get("display_name", "未知游戏")
                    count = result.get("count", 0)
                    leading_play = result.get("leading_play", "")
                    game_data.append(f"{game_name}  {count}({leading_play})")
                
                if game_data:
                    return {'success': True, 'data': game_data, 'proxy': proxy}
    except:
        pass
    
    return None

def get_game_data_and_push():
    """
    获取游戏数据并推送到微信
    """
    # 1. 获取代理列表
    proxy_list_url = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"
    proxies_to_test = []
    
    try:
        print("正在获取代理列表...")
        proxy_response = requests.get(proxy_list_url, timeout=10)
        if proxy_response.status_code == 200:
            proxy_lines = proxy_response.text.strip().split('\n')
            proxies_to_test = [line.strip() for line in proxy_lines if line.strip()]
            print(f"获取到 {len(proxies_to_test)} 个代理")
    except Exception as e:
        print(f"获取代理列表失败: {e}")
    
    # 2. 并发测试代理获取游戏数据
    url = "https://api.086378.com/v2/member/accumulation-statistic/?platform=1&group_tag=other&offset=0&limit=20"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.086378.com/',
    }
    
    game_data = []
    success = False
    
    print("开始并发测试代理...")
    
    # 使用线程池并发测试代理，最多同时测试10个
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有代理测试任务
        future_to_proxy = {
            executor.submit(test_proxy_and_fetch, proxy, url, headers): proxy 
            for proxy in proxies_to_test[:30]  # 只测试前30个代理，加快速度
        }
        
        # 获取第一个成功的结果
        for future in as_completed(future_to_proxy):
            result = future.result()
            if result and result['success']:
                game_data = result['data']
                print(f"✓ 成功获取数据！使用代理: {result['proxy']}")
                success = True
                # 取消其他未完成的任务
                for f in future_to_proxy:
                    f.cancel()
                break
    
    # 如果所有代理都失败，使用默认数据
    if not success:
        print("所有代理均失败，使用默认数据")
        game_data = [
            "数据获取中  0(--)",
            "请稍后查看  0(--)",
            "系统维护中  0(--)",
            "暂无数据  0(--)",
            "稍后重试  0(--)"
        ]
    
    try:
        token_url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appID}&secret={appSecret}'
        token_response = requests.get(token_url).json()
        access_token = token_response.get('access_token')
        
        if not access_token:
            print("获取access_token失败")
            return
        
        # 3. 准备推送数据
        today = datetime.date.today().strftime("%Y年%m月%d日")
        
        # 准备前5个游戏数据，每个作为独立字段
        push_data = {
            "touser": openId,
            "template_id": template_id,
            "data": {
                "game1": {"value": game_data[0] if len(game_data) > 0 else "无数据"},
                "game2": {"value": game_data[1] if len(game_data) > 1 else "无数据"},
                "game3": {"value": game_data[2] if len(game_data) > 2 else "无数据"},
                "game4": {"value": game_data[3] if len(game_data) > 3 else "无数据"},
                "game5": {"value": game_data[4] if len(game_data) > 4 else "无数据"},
                "date": {"value": today}
            }
        }
        
        # 4. 推送到微信
        push_url = f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}'
        
        # 设置正确的Content-Type和编码
        headers = {
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        result = requests.post(push_url, data=json.dumps(push_data, ensure_ascii=False).encode('utf-8'), headers=headers)
        
        # 只显示推送结果
        if '"errcode":0' in result.text:
            print("推送成功！")
        else:
            print(f"推送失败: {result.text}")
        
    except Exception as e:
        print(f"操作失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    get_game_data_and_push()
