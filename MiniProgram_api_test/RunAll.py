#！python3
import requests
import json
import logging
import random
import time
import os,sys
import xlrd
import datetime
import re
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import configparser

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
# 获取日志文件路径（根据当天来生成文件夹）
proDir = os.path.split(os.path.realpath(__file__))[0]
log_path = os.path.join(proDir,"Log",datetime.datetime.now().strftime("%Y%m%d"))
log_file = os.path.join(log_path,datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")+'.txt')

# 判断日志文件是否存在  不存在则创建
if not os.path.exists(log_path):
	os.mkdir(log_path)

# 设置日志格式
log_format = '[%(asctime)s] [%(levelname)s] %(message)s'
logging.basicConfig(format=log_format,filename=log_file,filemode='w',level=logging.WARNING)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter(log_format)
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# 读取配置文件
config_path = os.path.join(proDir,'config.ini')
config = configparser.ConfigParser()
config.read(config_path)
host = config.get("HTTP","host")

# 配置头信息token需要自行获取
defult_headers = {
		"User-Agent": "Mozilla/5.0 (Linux; Android 8.0; DUK-AL20 Build/HUAWEIDUK-AL20; wv) AppleWebKit/537.36\
				 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.143 Crosswalk/24.53.595.0 XWEB/155 MMWEBSDK/21 Mobile\
				  Safari/537.36 MicroMessenger/6.7.1321(0x26070030) NetType/WIFI Language/zh_CN MicroMessenger/6.7.1321(0x26070030)\
				  NetType/WIFI Language/zh_CN",
		"appcode": "400850322f464fad8b0193c865cd4dbf",
		"Accept-Encoding": "gzip",
		"charset": "utf-8",
		"content-type": "application/json",
		"Connection": "Keep-Alive",
		"content-type": "application/json",
	}

# 获取要运行的测试用例
testcase = input('输入要运行的测试用例名称:')

# 获取并执行测试用例
def run_test(testcase):
	testcase_file = testcase + ".xls"
	testcase_path = os.path.join(proDir,'TestCase',testcase_file)

	if not os.path.exists(testcase_path):
		testcase_file = testcase + ".xlsx"
		testcase_path = os.path.join(proDir,'TestCase',testcase_file)
		if not os.path.exists(testcase_path):
			print('测试用例',testcase,',该用例不存在')
			logging.error(testcase)
			logging.error('该测试用例不存在')

	testdata =  xlrd.open_workbook(testcase_path)
	# 通过索引来获取sheet页
	sheet = testdata.sheet_by_index(0)
	nrows = sheet.nrows
	# 创建参数传递的空字典
	correlation_dict = {}
	response_dict = {}
	
	for i in range(1, nrows):

		# 判断该用例是否执行,如果是no重新进入for循环
		if sheet.cell(i,10).value != 'Y':
			continue

		# 获取用例数据
		case_name = sheet.cell(i, 0).value
		request_method = sheet.cell(i, 4).value
		request_address = sheet.cell(i, 5).value
		request_data_type = sheet.cell(i, 6).value
		request_data = sheet.cell(i, 7).value
		check_points = sheet.cell(i, 8).value.split(';')
		correlations = sheet.cell(i, 9).value.split(';')
		request_headers = sheet.cell(i, 3).value.split(';')

		# 根据配置的host来获取excel中的host 分UAT和Production环境
		if host == 'UAT':
			request_host = sheet.cell(i,1).value
		elif host == 'Production':
			request_host = sheet.cell(i,2).value

		# reg1用来获取等号前内容的正则，reg2则是用来获取等号后的内容
		reg1 = u"(.*)="
		reg2 = u"=(.*)"


		# 如果不是第一行，则执行参数传递
		if i == 0:
			pass
		else:
			# 参数传递,不为空再继续
			for correlation in correlations:

				if correlations[0] == '':
					continue
				# 获取需要传递的key和value。组成correlation_dict
				correlation_key = ''.join(re.findall(reg1, correlation)).replace('\'', '')
				correlation_value = ''.join(re.findall(reg2, correlation))

				# 如果value以xls开头，则去使用参数化方法
				# if correlation_value.startswith("xls"):

				correlation_dict[correlation_key] = correlation_value
			for key in correlation_dict:
				# 对参数进行替换
				if request_data.find(key) > 0:
					request_data = request_data.replace(key, '"' + correlation_dict[key] + '"')
				if str(request_headers).find(key) > 0:
					request_headers = str(request_headers).replace(key,  correlation_dict[key]).replace('[','').replace(']','').replace('\'','')
				if request_address.find(key) > 0:
					request_address = request_address.replace(key, '"' + correlation_dict[key] + '"')

		# 请求头为空时，使用默认请求头
		if sheet.cell(i, 3).value == '':
			request_headers = defult_headers
		# 不为空时，将该请求头加入默认请求中
		else:
			add_headers_key = ''.join(re.findall(reg1, request_headers))
			add_headers_value = ''.join(re.findall(reg2, request_headers))
			# if add_headers_value.startswith('$'):
				
			defult_headers[add_headers_key] = add_headers_value
			request_headers = defult_headers
			

		


		request_url = request_host + request_address
				
		# 进行接口测试
		if request_method == 'get':
			result = requests.get(request_url,headers=request_headers,verify=False,allow_redirects=False)
			try:
				response = result.json()
			except Exception as error:
				logging.error(error)
		elif request_method == 'post':
			result = requests.post(request_url,headers=request_headers,data=request_data.encode("utf-8").decode("latin1"),verify=False,allow_redirects=False)
			try:
				response = result.json()
			except Exception as error:
				logging.error(error)

		# 传参数组
		for correlation in correlations:
			if correlations[0] == '':
				continue
			correlation_key = ''.join(re.findall(reg1, correlation)).replace('\'', '')
			correlation_value = ''.join(re.findall(reg2, correlation)).replace('response.headers','result.headers')
			try:
				correlation_dict[correlation_key] = eval(correlation_value).replace('"','')
			except Exception as e:
				logging.error("{}：{}".format(case_name, e))

		# 对结果进行断言
		if check_points[0]:
			for check_point in check_points:
				# 由于正则获得的是列表，用join方法转为字符串
				check_key = ''.join(re.findall(reg1, check_point))
				check_value = ''.join(re.findall(reg2, check_point))
				# 将字符串转为可执行代码
				try:
					response_key = eval(check_key)
				except Exception as e:
					logging.error("{}：KeyError{}".format(case_name, e))

				try:
					assert str(response_key) == str(check_value)
				except AssertionError as AssertError:
					logging.error("{}中,{} 不等于 {}".format(case_name, response_key, check_value))	
				except Exception as e:
					logging.error("{}：{}".format(case_name, e))
		else:
			print(case_name+',不需要断言')

		

			


	


# 判断需要执行的脚本
if testcase == '':
	rul_all()
else:
	run_test(testcase)


