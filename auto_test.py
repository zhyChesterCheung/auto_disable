import unittest
from load_write_mysql import read_data, insert_data, sleep_time, v3_get_last_qps, resource_least, resource_judge, alert, \
    Prometheus
from start_main import GetIdcBadPercent, ReportGenerator as RG
import HTMLTestRunner


# 单独测试load_write_mysql.py文件中每个模块
class load_write_mysql_test(unittest.TestCase):
    # 测试用例前执行
    def setUp(self):
        print('Case start...')
        pass

    # 测试用例后执行
    def tearDown(self):
        print('Case end...')
        print('\n')
        pass

    def test_sleep_time(self):
        ret = sleep_time(hour=1, min=2, sec=3)
        self.assertEqual(ret, 3723)
        print('test_sleep_time : ', ret)

    def test_v3_get_last_qps(self):
        ret = v3_get_last_qps()
        self.assertIsNotNone(ret)
        print('test_v3_get_last_qps : ', ret)
        return ret

    def test_resource_least(self):
        ret = v3_get_last_qps()
        ret = resource_least(ret)
        self.assertIsNotNone(ret)
        print('test_resource_least : ', ret)

    def test_resource_judge(self):
        ret = v3_get_last_qps()
        ret = resource_least(ret)
        ret = resource_judge(ret, 'cmcc')
        self.assertEqual(ret, True or False)
        print('test_resource_judge : ', ret)

    def test_alert(self):
        ret_1 = alert(1)
        self.assertIsNotNone(ret_1)
        print('test_alert : ', ret_1)
        ret_2 = alert(2)
        self.assertIsNotNone(ret_2)
        print('test_alert : ', ret_2)
        ret_3 = alert(3)
        self.assertIsNotNone(ret_3)
        print('test_alert : ', ret_3)
        ret_4 = alert(4)
        self.assertIsNotNone(ret_4)
        print('test_alert : ', ret_4)

        ret = ret_1 + ret_2 + ret_3 + ret_4
        print('total test_alert : ', ret)

    def test_Prometheus(self):
        ret = Prometheus('cmcc')
        self.assertEqual(ret, True or False)
        print('test_Prometheus : ', ret)


# 单独测试start_main.py文件中每个模块
class start_main_test(unittest.TestCase):
    # 测试用例前执行
    def setUp(self):
        print('Case Begin...')
        pass

    # 测试用例后执行
    def tearDown(self):
        print('Case Over...')
        print('\n')
        pass

    def test_GetIdcBadPercent(self):
        ret = GetIdcBadPercent(idc='good', isp='NA')
        self.assertEqual(ret, 0.3)

        ret = GetIdcBadPercent(idc='saopaulo', isp='NA')
        self.assertEqual(ret, 0.5)

        ret = GetIdcBadPercent(idc='good', isp='chang')
        self.assertEqual(ret, 0.25)

    def test_GetServerLoadInfo(self):
        ret = RG.GetServerLoadInfo(self=RG, idc='changsha-cmcc')
        self.assertIn('Traffic', ret)
        print('test_GetServerLoadInfo : ', ret)

    def test_Votest(self):
        ret = RG.Votest(self=RG, idc='changsha-cmcc', isp='DRPENG')
        self.assertIn(str(ret), 'None')
        print('test_Votest : ', str(ret))

    def test_IsNeedDisable(self):
        ret = RG.IsNeedDisable(self=RG, idc='', idc_warnning='Votest:↑good,↓good')
        self.assertEqual(ret, False)
        print('test_IsNeedDisable : ', ret)

        ret = RG.IsNeedDisable(self=RG, idc='', idc_warnning='Votest:↑good,↓bad')
        self.assertEqual(ret, True)
        print('test_IsNeedDisable : ', ret)

    def test_checkout(self):
        sql2 = "select * from disable_idc"
        result = read_data(sql=sql2)
        idc = 'zen-dalas'
        if idc in str(result):
            self.assertIn(idc, str(result))
            print("test_checkout : ", "yes")
        else:
            self.assertNotIn(idc, str(result))
            print("test_checkout : ", "no")

    def test_disable(self):
        idc = 'zen-dalas'
        sql3 = "INSERT INTO disable_idc (idc, disableStatus) VALUES ('%s', 1)" % idc
        insert_data1 = insert_data(sql=sql3)
        sql2 = "select * from disable_idc"
        ret = read_data(sql=sql2)
        if idc in str(ret):
            self.assertIn(idc, str(ret))
            print('test_disable : ', 'yes')
        else:
            self.assertNotIn(idc, str(ret))
            print('test_disable : ', 'no')

    def test_goback(self):
        sql4 = "select * from disable_idc where disableStatus = '1'"
        result = read_data(sql=sql4)
        idc = 'zen-dalas'
        sql3 = "INSERT INTO disable_idc (idc, disableStatus) VALUES ('%s', 1)" % idc
        insert_data1 = insert_data(sql=sql3)
        if idc in str(result):
            sql5 = "delete from disable_idc where idc='%s'" % idc
            insert_data2 = insert_data(sql=sql5)
            if idc in insert_data2:
                self.assertIn('test_goback : ', 'no')
            else:
                self.assertNotIn('test_goback : ', 'yes')
        else:
            self.assertEqual(result, 'None')


class logistic_test(unittest.TestCase):
    data = []

    # 测试用例前执行
    def setUp(self):
        print('Case Begin...')
        pass

    # 测试用例后执行
    def tearDown(self):
        print('Case Over...')
        print('\n')
        pass

    def test_loadClusters(self):
        stats = RG()
        ret = stats.loadClusters(host_="125.88.159.162", port_=3315, user_="uap_auto_disable",
                                 password_="f*j4SfWC4EHv3_x*Brtw", db_="agora_resource")
        print('clusters : ', ret)
        stats.idcs.append(ret)
        self.assertIn('CMCC', str(ret))
        print('test_loadClusters : ', ret)


# 定义一个测试集合，方便添加Case
def suite():
    suiteTest = unittest.TestSuite()

    # suiteTest.addTest(load_write_mysql_test("test_insert_data"))
    suiteTest.addTest(logistic_test("test_loadClusters"))
    suiteTest.addTest(start_main_test("test_GetIdcBadPercent"))
    suiteTest.addTest(start_main_test("test_GetServerLoadInfo"))
    suiteTest.addTest(start_main_test("test_Votest"))
    suiteTest.addTest(start_main_test("test_IsNeedDisable"))
    suiteTest.addTest(start_main_test("test_checkout"))
    suiteTest.addTest(load_write_mysql_test("test_v3_get_last_qps"))
    suiteTest.addTest(load_write_mysql_test("test_resource_least"))
    suiteTest.addTest(load_write_mysql_test("test_resource_judge"))
    suiteTest.addTest(load_write_mysql_test("test_Prometheus"))
    suiteTest.addTest(start_main_test("test_disable"))
    suiteTest.addTest(start_main_test("test_goback"))
    suiteTest.addTest(load_write_mysql_test("test_alert"))
    suiteTest.addTest(load_write_mysql_test("test_sleep_time"))

    return suiteTest


if __name__ == '__main__':
    # filename = '/Users/zhy/PycharmProjects/test_pycharm_project/testresult.html'  # 测试报告的存放路径及文件名
    filename = '/home/devops/disable_tools/testresult.html'
    fp = open(filename, 'wb')

    suite = suite()

    runner = HTMLTestRunner.HTMLTestRunner(stream=fp, title='测试报告', description='测试结果如下: ')
    runner.run(suite)
    fp.close()
