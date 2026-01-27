# 简化版游戏数据推送到微信公众号
import os
import requests
import json
import curl_cffi.requests
import datetime

# 微信公众号配置 - 可以直接填写或使用环境变量
appID = os.environ.get("APP_ID", "wx06948af05ffacf02")
appSecret = os.environ.get("APP_SECRET", "68942a7b76350d5c9bcd9b3cfc57e0bd")
openId = os.environ.get("OPEN_ID", "owzvx2FPYTAZGfb_os0AoZkd4UeY")
template_id = os.environ.get("TEMPLATE_ID", "yiNc0QFCcdBsKuJ48CATDOEg-3k0XD9gWAlQX9dQJSw")

def get_game_data_and_push():
    """
    获取游戏数据并推送到微信
    """
    # 1. 获取游戏数据
    url = "https://api.086378.com/v2/member/accumulation-statistic/?platform=1&group_tag=other&offset=0&limit=20"
    
    try:
        # 使用curl_cffi发送GET请求，模拟Chrome浏览器，添加更多请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.086378.com/',
        }
        
        # 添加重试机制
        max_retries = 3
        game_data = []
        
        for attempt in range(max_retries):
            try:
                # 先尝试用 requests 库
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=15
                )
                
                # 如果 requests 失败，再用 curl_cffi
                if response.status_code != 200:
                    response = curl_cffi.requests.get(
                        url, 
                        headers=headers,
                        impersonate="chrome120", 
                        timeout=15
                    )
                
                response.raise_for_status()
                json_data = response.json()
                
                # 提取游戏数据
                if "data" in json_data and "results" in json_data["data"]:
                    results = json_data["data"]["results"]
                    
                    for result in results:
                        game_name = result.get("game", {}).get("display_name", "未知游戏")
                        count = result.get("count", 0)
                        leading_play = result.get("leading_play", "")
                        game_data.append(f"{game_name}  {count}({leading_play})")
                    break  # 成功获取数据，跳出重试循环
                    
            except Exception as e:
                print(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)  # 等待2秒后重试
                else:
                    print("获取游戏数据失败，使用默认数据")
                    # 如果获取失败，使用默认数据
                    game_data = [
                        "数据获取中  0(--)",
                        "请稍后查看  0(--)",
                        "系统维护中  0(--)",
                        "暂无数据  0(--)",
                        "稍后重试  0(--)"
                    ]
        
        # 2. 获取微信access_token
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
