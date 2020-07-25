#!/usr/bin/python
# -*- coding: utf-8 -*-
import base64
import urllib
import pymysql
import time
import requests
import json
import influxdb
import traceback
import os, sys
import logging

host = '127.0.0.1'
port = 3335
user = 'autoDisable'
password = 's34hjdj^KFJ1'
datab = 'uap_database'
charset = 'utf8mb4'

# 从app center的数据库表中读取数据判断idc和ip的状态
def read_data(sql):
    data_table = ()
    try:
        db1 = pymysql.connect(host=host, port=port, user=user, password=password, db=datab, charset=charset)
        cursor = db1.cursor(cursor=pymysql.cursors.DictCursor)

        line = cursor.execute(sql)
        data = cursor.fetchall()

        data_table = data

        db1.commit()
        cursor.close()
        db1.close()

    except Exception as msg:

        logging.warning(msg)

    return data_table

# 向SRE的禁用数据库中写入禁用数据
def insert_data(sql):
    try:
        db2 = pymysql.connect(host=host, port=port, user=user, password=password, db=datab, charset=charset)  # 打开数据库连接
        cursor = db2.cursor(cursor=pymysql.cursors.DictCursor)  # 创建游标对象

        line = cursor.execute(sql)
        data = cursor.fetchall()
        data_table = data

        db2.commit()
        cursor.close()
        db2.close()
    except Exception as msg:
        logging.warning(msg)

# 定义每次检测机房状态的周期
def sleep_time(hour, min, sec):
    return hour * 3600 + min * 60 + sec

# 从公司Prometheus获取资源余量
def v3_get_last_qps():
    now_ts = int(time.time())
    query = 'min(1 - uap_mix_streaming_appCenter_resourceIspUsage_usage{instance=~"120.131.12.101.*|120.24.80.42.*|47.111.233.232.*|101.133.175.161.*|101.200.232.192.*|47.115.148.104.*|47.114.52.104.*",isp=~"AP|CMCC|CUCC|CTEL|NA|VN|EU"}) by (isp)'

    params = {
        'query': query,
        'start': now_ts - 60,
        'end': now_ts,
        'step': '1m',
    }
    url = 'http://175.6.6.12:9090/api/v1/query_range?'
    token = 'autoDisable' + ':' + 's34hjdj^KFJ1'
    token = base64.b64encode(token.encode())
    token = b'Basic' + token

    req = urllib.request.Request(url=url + urllib.parse.urlencode(params),
                                 headers={'Authorization': token},
                                 method='GET')
    ret = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    return ret

# 解析数据，计算资源余量
def resource_least(last_gps):
    gps_data = last_gps['data']
    result_data = gps_data['result']

    info = []
    val = ''
    for i in range(len(result_data)):
        sub = result_data[i]
        num = 0
        for j in sub.keys():
            value = sub[j]

            num = num + 1
            if num == 1:

                for key, val in value.items():

                    logging.warning(str(val))
            else:

                value[0] = list(map(float, value[0]))
                value[1] = list(map(float, value[1]))

                minist = min(value[0][1], value[1][1])

                key_data = val
                info_temp = {key_data: minist}
                info.append(info_temp)

    return info

# 对当前资源余量进行判断，充足返回True，不足返回False
def resource_judge(least_data, region):

    for i in range(len(least_data)):
        value = least_data[i]
        if type(value) == 'list':
            return False
        else:

            logging.warning(value)
            for key, val in value.items():

                logging.warning('key, val is : ', key, val)
                logging.warning('isp : ', region.upper(), type(region))
                logging.warning(key + " : " + str(val))

                if str(key) == str(region.upper()):
                    if val >= 0.3:
                        return True
                    else:
                        return False

    return True

# 企业微信报警信息发送
def alert(chose, group='', ret=''):
    url = 'https://agolet.agoralab.co/v1/agobot/message'
    if chose == 1:
        json_data = {
            "channel": "APP center_alert",
            "body": "mix_streaming alert" + '\n idc : ' + str(group) + '\n' + str(ret),
            "uid": 1886000234233856,
            "token": "653d8112ab1151112a9dda5cb49031ed0dc4208b26a3bb840ddc8ef7c1bc6368"
        }
        logging.warning("attention info_1 .....")
    elif chose == 2:
        json_data = {
            "channel": "APP center_alert",
            "body": "mix_streaming autoDisable fail" + '\n idc is : ' + str(group) + '\n' + str(ret),
            "uid": 1886000234233856,
            "token": "653d8112ab1151112a9dda5cb49031ed0dc4208b26a3bb840ddc8ef7c1bc6368"
        }
        logging.warning("attention info_2 ......")
    elif chose == 3:
        json_data = {
            "channel": "APP center_alert",
            "body": "mix_treaming has restored" + '\n idc is : ' + str(group) + '\n' + str(ret),
            "uid": 1886000234233856,
            "token": "653d8112ab1151112a9dda5cb49031ed0dc4208b26a3bb840ddc8ef7c1bc6368"
        }
        logging.warning("attention info_3 ......")
    elif chose == 4:
        json_data = {
            "channel": "APP center_alert",
            "body": "mix_streaming" + ' idc : ' + str(group) + 'autoDisable finished' + '\n' + str(ret),
            "uid": 1886000234233856,
            "token": "653d8112ab1151112a9dda5cb49031ed0dc4208b26a3bb840ddc8ef7c1bc6368"
        }
        logging.warning("attention info_4 ......")
    r = requests.post(url, data=json_data)

    logging.warning(r.text)

def Prometheus(region):
    # 获取PROMETHEUS实时数据
    last_qps = v3_get_last_qps()

    logging.warning('load_qps : ', last_qps)

    # 获取idc和ip的剩余资源余量
    least_data = resource_least(last_qps)

    logging.warning('least_data : ', least_data)

    # 判断当前资源余量是否充足
    sign = resource_judge(least_data=least_data, region=region)

    logging.warning('sign : ', sign)

    return sign

if __name__ == '__main__':
    host = sys.argv[1]
    port = sys.argv[2]
    user = sys.argv[3]
    password = sys.argv[4]
    datab = sys.argv[5]
    charset = 'utf8mb4'  # 编码
    os.system("python3 start_main.py")
