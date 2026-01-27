# 简化版游戏数据推送到微信公众号
import os
import requests
import json
import curl_cffi.requests
import datetime
import re
import time

# 微信公众号配置 - 可以直接填写或使用环境变量
appID = os.environ.get("APP_ID", "wx06948af05ffacf02")
appSecret = os.environ.get("APP_SECRET", "68942a7b76350d5c9bcd9b3cfc57e0bd")
openId = os.environ.get("OPEN_ID", "owzvx2FPYTAZGfb_os0AoZkd4UeY")
template_id = os.environ.get("TEMPLATE_ID", "yiNc0QFCcdBsKuJ48CATDOEg-3k0XD9gWAlQX9dQJSw")

# 亚洲国家代码列表
ASIAN_COUNTRIES = {
    'CN', 'JP', 'KR', 'TW', 'HK', 'SG', 'TH', 'VN', 'MY', 'ID', 'PH', 'IN', 
    'PK', 'BD', 'MM', 'KH', 'LA', 'MN', 'NP', 'LK', 'AF', 'BT', 'BN', 'KP',
    'MV', 'TL', 'MO', 'AE', 'SA', 'IQ', 'IR', 'IL', 'JO', 'KW', 'LB', 'OM',
    'QA', 'SY', 'YE', 'BH', 'PS', 'AM', 'AZ', 'GE', 'KZ', 'KG', 'TJ', 'TM', 'UZ'
}

def extract_ip_from_proxy(proxy):
    """
    从代理字符串中提取IP地址
    """
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', proxy)
    return match.group(1) if match else None

def check_ip_location_batch(ips):
    """
    批量检查IP是否在亚洲
    """
    if not ips:
        return {}
    
    asian_ips = {}
    
    try:
        # 分批处理，每次最多100个IP
        batch_size = 100
        for i in range(0, len(ips), batch_size):
            batch = ips[i:i+batch_size]
            
            # 使用 ip-api.com 的批量查询接口
            response = requests.post(
                'http://ip-api.com/batch',
                json=batch,
                params={'fields': 'status,countryCode,query'},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                for result in results:
                    if result.get('status') == 'success':
                        ip = result.get('query')
                        country_code = result.get('countryCode', '')
                        # 检查是否是亚洲国家
                        if country_code in ASIAN_COUNTRIES:
                            asian_ips[ip] = country_code
                            print(f"✓ 亚洲IP: {ip} ({country_code})")
            
            # 避免请求过快
            if i + batch_size < len(ips):
                time.sleep(1)
                
    except Exception as e:
        print(f"批量检查IP位置失败: {e}")
    
    return asian_ips

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
            # 保留所有类型的代理
            all_proxies = [line.strip() for line in proxy_lines if line.strip()]
            print(f"获取到 {len(all_proxies)} 个代理")
            
            # 提取所有IP地址
            print("正在提取IP地址...")
            ip_to_proxy = {}
            for proxy in all_proxies:
                ip = extract_ip_from_proxy(proxy)
                if ip:
                    if ip not in ip_to_proxy:
                        ip_to_proxy[ip] = []
                    ip_to_proxy[ip].append(proxy)
            
            all_ips = list(ip_to_proxy.keys())
            print(f"提取到 {len(all_ips)} 个唯一IP")
            
            # 批量检查IP是否在亚洲
            print("正在批量检查IP归属地...")
            asian_ips = check_ip_location_batch(all_ips)
            print(f"找到 {len(asian_ips)} 个亚洲IP")
            
            # 只保留亚洲的代理
            asian_proxies = []
            for ip in asian_ips:
                asian_proxies.extend(ip_to_proxy[ip])
            
            proxies_to_test = asian_proxies
            print(f"过滤后剩余 {len(proxies_to_test)} 个亚洲代理")
            
    except Exception as e:
        print(f"获取代理列表失败: {e}")
    
    # 2. 获取游戏数据
    url = "http://api.086378.com/v2/member/accumulation-statistic/?platform=1&group_tag=other&offset=0&limit=20"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.086378.com/',
    }
    
    game_data = []
    success = False
    
    # 遍历代理列表尝试获取数据
    for i, proxy in enumerate(proxies_to_test, 1):  # 测试所有代理
        if success:
            break
            
        try:
            print(f"尝试代理 {i}/{len(proxies_to_test)}: {proxy[:50]}...")
            
            # 根据代理类型设置不同的代理格式
            if proxy.startswith('socks5://'):
                # SOCKS5 代理
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
            elif proxy.startswith('socks4://'):
                # SOCKS4 代理
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
            elif proxy.startswith('http://'):
                # HTTP 代理
                proxies = {
                    'http': proxy,
                    'https': proxy.replace('http://', 'https://')  # HTTP代理也用于HTTPS
                }
            elif proxy.startswith('https://'):
                # HTTPS 代理
                proxies = {
                    'http': proxy.replace('https://', 'http://'),
                    'https': proxy
                }
            else:
                # 格式不正确，跳过
                continue
            
            response = curl_cffi.requests.get(
                url, 
                headers=headers,
                proxies=proxies,
                impersonate="chrome120", 
                timeout=7  # 缩短超时到5秒
            )
            
            if response.status_code == 200:
                json_data = response.json()
                
                # 提取游戏数据
                if "data" in json_data and "results" in json_data["data"]:
                    results = json_data["data"]["results"]
                    
                    for result in results:
                        game_name = result.get("game", {}).get("display_name", "未知游戏")
                        count = result.get("count", 0)
                        leading_play = result.get("leading_play", "")
                        game_data.append(f"{game_name}  {count}({leading_play})")
                    
                    if game_data:
                        print(f"✓ 成功！代理: {proxy[:30]}...")
                        success = True
                        break
                        
        except Exception as e:
            # 静默失败，继续尝试下一个代理
            pass
    
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
