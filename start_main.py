#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import traceback
from collections import defaultdict
import influxdb
import pymysql
import logging
import sys
from load_write_mysql import alert, Prometheus, sleep_time, read_data, insert_data

clientread = influxdb.InfluxDBClient('influxdb-quality-report.sh.agoralab.co', 80, 'qualityread', 'agorabestvoip',
                                     'quality_report')
service_name = "voice"
service_column = "voserver"
service_group = "SD-RTN OnCall Group"

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"

logging.basicConfig(filename='autoDisable.log', level=logging.WARNING, format=LOG_FORMAT, datefmt=DATE_FORMAT)


def GetIdcBadPercent(idc, isp):
    if "johannesburg" in idc or "saopaulo" in idc or 'taiwan' in idc:
        return 0.5
    if isp == "NA":
        return 0.3
    return 0.25


class ReportGenerator(object):

    def __init__(self):
        self.idcs = []

        self.conn = pymysql.connect(host="125.88.159.162", port=3315, user="uap_auto_disable",
                                    password="f*j4SfWC4EHv3_x*Brtw", db="agora_resource")
        self.dict_uap = {}

    def GetServerLoadInfo(self, idc):
        ret = ""
        sql = "select sum(user_load) as user_load from (select mean(load) as user_load from %s_service_load where " \
              "time <= now() and time >= now() - 5m and idc = '%s' group by time(1m), idc, ip, vosid) group by" \
              " time(1m), idc" % (service_name, idc)
        rs = clientread.query(sql)
        for x, y in rs.items():
            for z in y:
                load = int(z['user_load'])
                ret = "Load:%s" % load
                break
        sql = "select sum(traffic_in) as traffic_in, sum(traffic_out) as traffic_out  from (select mean(traffic_in) as" \
              " traffic_in, mean(traffic_out) as traffic_out from %s_service_load where time <= now() and " \
              "time >= now() - 5m and idc = '%s' group by time(1m), ip) group by time(1m), idc" % (service_name, idc)
        rs = clientread.query(sql)
        for x, y in rs.items():
            for z in y:
                tin = float(z['traffic_in']) / 1000 / 1000
                tout = float(z['traffic_out']) / 1000 / 1000
                ret = "%s Traffic:↑%.2fGbps,↓%.2fGbps" % (ret, tin, tout)
                break
        return ret

    def loadClusters(self, host_, port_, user_, password_, db_):
        conn = pymysql.connect(
            host=host_, port=port_, user=user_, passwd=password_, db=db_)
        cur = conn.cursor()
        cur.execute("SELECT idc,detail_ip FROM servers where %s=1 and down_time >= now() group by idc" % service_column)
        data = cur.fetchall()

        for (idc, detail_ip) in data:
            for x in detail_ip.split(";"):
                self.idcs.append((idc, x.split(":")[0]))

        cur.close()
        conn.close()

    # 获得Votest数据
    def Votest(self, idc, isp):
        if isp == 'DRPENG' or idc == 'DRPENG':
            return
        to = 'good'
        ffrom = 'good'
        sql = "select mean(lost) as lost from votest_quality where time > now() - 6m and from_idc='%s' and " \
              "from_isp = '%s' and from_isp = to_isp group by time(1m), from_idc, from_isp, to_idc" % (idc, isp)
        rs = clientread.query(sql)
        total = defaultdict(int)
        lost5 = defaultdict(int)
        lost10 = defaultdict(int)
        for x, y in rs.items():

            for z in y:

                total[z['time']] += 1

                z['lost'] = int(0 if z['lost'] is None else z['lost'])
                if z['lost'] > 5:
                    lost5[z['time']] += 1
                if z['lost'] > 10:
                    lost10[z['time']] += 1
        bad = 0
        bad2 = 0
        for (tm, lost) in lost5.items():
            if float(lost) / float(total[tm]) > GetIdcBadPercent(idc, isp):
                bad += 1

        for (tm, lost) in lost10.items():
            if float(lost) / float(total[tm]) > GetIdcBadPercent(idc, isp):
                bad2 += 1

        if bad >= 3:
            ffrom = 'bad'
        if bad2 >= 3:
            ffrom = 'fatal'
        if bad2 >= 5:
            ffrom = 'disaster'
        if len(total) < 2:
            ffrom = '-'

        sql = "select mean(lost) as lost from votest_quality where time > now() - 6m and to_idc='%s' and to_isp = " \
              "'%s' and from_isp = to_isp group by time(1m), from_idc, to_isp, to_idc" % (idc, isp)

        rs = clientread.query(sql)
        total = defaultdict(int)
        lost5 = defaultdict(int)
        lost10 = defaultdict(int)
        for x, y in rs.items():

            for z in y:

                total[z['time']] += 1
                z['lost'] = int(0 if z['lost'] is None else z['lost'])
                if z['lost'] > 5:
                    lost5[z['time']] += 1
                if z['lost'] > 10:
                    lost10[z['time']] += 1

        bad = 0
        bad2 = 0
        for (tm, lost) in lost5.items():
            if float(lost) / float(total[tm]) > GetIdcBadPercent(idc, isp):
                bad += 1

        for (tm, lost) in lost10.items():
            if float(lost) / float(total[tm]) > GetIdcBadPercent(idc, isp):
                bad2 += 1

        if bad >= 3:
            to = 'bad'
        if bad2 >= 3:
            to = 'fatal'
        if bad2 >= 5:
            ffrom = 'disaster'
        if len(total) <= 2:
            to = '-'

        return "Votest:↑%s,↓%s" % (to, ffrom)

    def IsNeedDisable(self, idc, idc_warnning):
        if 'bad' in idc_warnning or 'fatal' in idc_warnning or 'disaster' in idc_warnning:
            return True
        elif 'good' not in idc_warnning:
            return True
        else:
            return False

    def split_isp(self, host_, port_, user_, password_, db_):
        idcs_uap = []
        idcs_new = []
        conn = pymysql.connect(
            host=host_, port=port_, user=user_, passwd=password_, db=db_)
        cur = conn.cursor()
        cur.execute("SELECT cluster, country FROM clusters")
        data = cur.fetchall()

        logging.warning(data)
        for i in data:
            self.dict_uap[i[0]] = i[1]

            logging.warning(self.dict_uap)

        for i in self.idcs:
            if i[0] in self.dict_uap:
                idcs_new.append((i[0], self.dict_uap[i[0]]))
            else:
                continue

        AP = ['HK', 'TW', 'JP', 'KP', 'KR', 'MN', 'BD', 'BT', 'IO', 'IN', 'MV', 'NP', 'PK', 'LK', 'BN', 'KH', 'TL',
              'ID', 'LA', 'MY', 'MM', 'PH', 'SG', 'TH', 'AU', 'NZ', 'FM', 'PF']
        VN = ['VN']

        for i in idcs_new:

            if str(i[1]) in AP:
                idcs_uap.append((str(i[0]), 'AP'))
            elif str(i[1]) in VN:
                idcs_uap.append((str(i[0]), 'VN'))
            elif str(i[1]) == 'CN':
                idcs_uap.append((str(i[0]), str(i[0].split('-')[1])))
            else:
                idcs_uap.append((str(i[0]), 'NA'))

        logging.warning(idcs_uap)
        return idcs_uap

    # 处理禁用逻辑和恢复禁用逻辑
    def do_DisableLogic(self, stats):
        while True:

            stats.loadClusters("125.88.159.162", 3315, "uap_auto_disable", "f*j4SfWC4EHv3_x*Brtw",
                               "agora_resource")

            error = False

            # 根据UAP业务排除多余的大网业务
            idcs_uap = stats.split_isp("127.0.0.1", 3335, "autoDisable", "s34hjdj^KFJ1", "uap_database")

            for (idc, region) in idcs_uap:

                try:
                    idc_warnning = "%s" % (stats.Votest(idc, region))


                    if '-' in idc_warnning:
                        continue

                    # 处理禁用逻辑
                    if stats.IsNeedDisable(idc, idc_warnning):

                        # 判断idc在disable_idc中是否已经禁用
                        sql2 = "select * from disable_idc"
                        result = read_data(sql=sql2)
                        for i in range(len(result)):
                            if idc is result[i]['idc']:
                                continue
                            else:
                                pass

                        service_info = stats.GetServerLoadInfo(idc)

                        logging.warning('service_info is : ' + service_info)
                        ret = "service_name : %s \n idc : %s \n region : %s \n idc_warnning : %s \n service_info : %s" % (
                            service_name, idc, region, idc_warnning, service_info)

                        logging.warning('ret is : ' + ret)

                        # 第一次报警
                        alert(chose=1, group=idc, ret=ret)

                        sign = Prometheus(region=region)
                        # 如果资源余量不足，不自动禁用，再次发送禁用失败报警信息
                        if not sign:
                            alert(chose=2, group=idc, ret=ret)
                        # 如果资源余量充足，自动开启禁用
                        else:
                            sql3 = "INSERT INTO disable_idc (idc, disableStatus) VALUES ('%s', 'yes')" % idc
                            insert_data(sql=sql3)
                            alert(chose=4, group=idc, ret=ret)

                    # 处理恢复禁用逻辑
                    else:
                        service_info = stats.GetServerLoadInfo(idc)

                        logging.warning('service_info is : ' + service_info)
                        ret = "service_name : %s \n idc : %s \n region : %s \n idc_warnning : %s \n service_info : %s" % (
                            service_name, idc, region, idc_warnning, service_info)
                        sql4 = "select * from disable_idc where disableStatus = 'yes'"
                        result = read_data(sql=sql4)

                        for i in range(len(result)):
                            if idc is result[i]['idc']:
                                # disableStatus字段为'yes'，则为自动禁用，否则手动禁用不作处理
                                alert(chose=3, group=idc, ret=ret)
                                sql5 = "delete from disable_idc where idc='%s'" % idc
                                insert_data(sql=sql5)

                except Exception as e:
                    error = True
                    traceback.print_exc()
                    logging.exception(e)

            if error:
                continue

            # 定时检测预警
            time.sleep(second)


if __name__ == "__main__":
    stats = ReportGenerator()

    second = sleep_time(0, 2, 0)
    stats.do_DisableLogic(stats)
