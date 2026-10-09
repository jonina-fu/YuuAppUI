import datetime
import os
import time

import requests
import sys
import json
from datetime import datetime
import re

import env_loader  # noqa: F401  # 加载同目录 .env（密钥不入库）

def get_timestamp(time_str):

    # time_str = 'Mon, 28 Aug 2023 10:03:52 +0000'
    timestamp = float('inf')
    try:
        parsed_time = datetime.strptime(time_str, '%a, %d %b %Y %H:%M:%S %z')
        timestamp = int(parsed_time.timestamp())
    except:
        return float('inf')

    return timestamp


def get_otp(phone_num, env,time_out = 600):
    # Twilio 账号 SID 与 basic auth 均在 .env（TWILIO_SID_SIT/UAT、TWILIO_AUTH_SIT/UAT）
    if env.lower() == 'sit':
        sid = os.getenv('TWILIO_SID_SIT', '')
        auth = 'Basic ' + os.getenv('TWILIO_AUTH_SIT', '')
    else:
        sid = os.getenv('TWILIO_SID_UAT', '')
        auth = 'Basic ' + os.getenv('TWILIO_AUTH_UAT', '')
    base_url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json?To=%s&PageSize=1'

    url = base_url % phone_num
    headers = {
        'Authorization': auth
    }

    # print(f"headers is {headers}")
    # print(f"url is {url}")

    current_timestamp = int(time.time())
    response = requests.request('GET', url, headers=headers)
    response_json = response.json()
    print(response_json)
    messages = response_json.get('messages')
    if messages and len(messages) > 0:
        # print(f"len(messages) is {len(messages)}")
        # return messages[0].get('body')
        messageReturn = ""
        date_created = float('inf')
        for i in range(len(messages)):
            messageReturn+=messages[i].get('body') + "\n"
            date_created = min(get_timestamp(messages[i].get('date_created')),date_created)
            # print(f"没判断时间是否过期 date_created is {date_created}")
            print(f"messageReturn is {messageReturn}")

        if abs(current_timestamp - date_created) < time_out:
            print(f"date_created is {date_created}")
            match = re.search(r'\d{4,}', messageReturn)
            matched_str = match.group()
            if matched_str is None:
                print("没有在短信内容中匹配到长度大于等于4的连续数字，将返回短信完整内容")
                return messageReturn
            else:
                return matched_str
        else:
            return 'messages expired'
    else:
        return 'No messages found'

if __name__ == "__main__":
    # print(get_otp(sys.argv[1], sys.argv[2]))
    # pass
    # 8613613008664 ， +8618049779775，8613613000001
    print(get_otp("+8613613008664", "SIT"))