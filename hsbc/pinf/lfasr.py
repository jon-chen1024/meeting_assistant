# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import os
import time
import requests
import urllib

lfasr_host = 'https://raasr.xfyun.cn/v2/api'
# 请求的接口名
api_upload = '/upload'
api_get_result = '/getResult'


class RequestApi(object):
    def __init__(self, appid, secret_key, upload_file_path):
        self.end_text = ""
        self.appid = appid
        self.secret_key = secret_key
        self.upload_file_path = upload_file_path
        self.ts = str(int(time.time()))
        self.signa = self.get_signa()

    def get_signa(self):
        appid = self.appid
        secret_key = self.secret_key
        m2 = hashlib.md5()
        m2.update((appid + self.ts).encode('utf-8'))
        md5 = m2.hexdigest()
        md5 = bytes(md5, encoding='utf-8')
        # 以secret_key为key, 上面的md5为msg， 使用hashlib.sha1加密结果为signa
        signa = hmac.new(secret_key.encode('utf-8'), md5, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        return signa


    def upload(self):
        print("上传部分：")
        upload_file_path = self.upload_file_path
        file_len = os.path.getsize(upload_file_path)
        file_name = os.path.basename(upload_file_path)

        param_dict = {}
        param_dict['appId'] = self.appid
        param_dict['signa'] = self.signa
        param_dict['ts'] = self.ts
        param_dict["fileSize"] = file_len
        param_dict["fileName"] = file_name
        param_dict["duration"] = "200"
        print("upload参数：", param_dict)
        data = open(upload_file_path, 'rb').read(file_len)

        response = requests.post(url =lfasr_host + api_upload+"?"+urllib.parse.urlencode(param_dict),
                                headers = {"Content-type":"application/json"},data=data)
        print("upload_url:",response.request.url)
        result = json.loads(response.text)
        print("upload resp:", result)
        return result


    def get_result(self):
        uploadresp = self.upload()
        orderId = uploadresp['content']['orderId']
        param_dict = {}
        param_dict['appId'] = self.appid
        param_dict['signa'] = self.signa
        param_dict['ts'] = self.ts
        param_dict['orderId'] = orderId
        param_dict['resultType'] = "transfer,predict"
        print("")
        print("查询部分：")
        print("get result参数：", param_dict)
        status = 3
        # 建议使用回调的方式查询结果，查询接口有请求频率限制
        while status == 3:
            response = requests.post(url=lfasr_host + api_get_result + "?" + urllib.parse.urlencode(param_dict),
                                     headers={"Content-type": "application/json"})
            # print("get_result_url:",response.request.url)
            result = json.loads(response.text)
            print(result)
            status = result['content']['orderInfo']['status']
            print("status=",status)
            if status == 4:
                break
            time.sleep(5)
            if status == -1:
                self.analysis_result(result)

        print("end_text:"+self.end_text)
        self.content_summary(self.end_text)

        print("get_result resp:",result)
        return result


    def analysis_result(self,data):
        """
        从嵌套的JSON字符串中提取并拼接出最终的文本结果。

        :param data: 包含嵌套JSON数据的字典
        :return: 提取并拼接后的文本结果
        """
        try:
            # 初始化一个空列表来存储所有提取的单词
            all_words = []

            # 获取orderResult字段的内容
            order_result_str = data['content']['orderResult']

            # 解析内部的JSON字符串
            order_result_data = json.loads(order_result_str)

            # 遍历每个包含json_1best字段的对象
            for lattice_item in order_result_data['lattice']:
                inner_json_str = lattice_item['json_1best']

                # 解析内部的JSON字符串
                inner_data = json.loads(inner_json_str)

                # 使用列表推导式提取st -> rt -> ws -> cw -> w 字段的值
                words = [item['cw'][0]['w'] for item in inner_data['st']['rt'][0]['ws']]

                # 将提取的单词添加到总的单词列表中
                all_words.extend(words)

            # 拼接成最终的文本结果，并去除多余的空字符串
            self.end_text = ''.join(word for word in all_words if word.strip())

        except json.JSONDecodeError as e:
            print(f"JSON 解码错误: {e}")
            return None
        except KeyError as e:
            print(f"键错误: {e}")
            return None
        except Exception as e:
            print(f"其他错误: {e}")
            return None
    def content_summary(self,end_text):

        url = "https://api.siliconflow.cn/v1/chat/completions"

        payload = {
            "model": "Qwen/QwQ-32B",
            "messages": [
                {
                    "role": "user",
                    "content": f"{end_text}"
                }
            ],
            "stream": False,
            "max_tokens": 512,
            "stop": None,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "response_format": {"type": "text"},
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "description": "生成100字内的总结，并将总结写入新字段",
                        "name": "<string>",
                        "parameters": {},
                        "strict": False
                    }
                }
            ]
        }
        headers = {
            "Authorization": "Bearer sk-jncftpdfzxaffluqbhswlnkureqgxnctjlbyrvelhwrvwxli",
            "Content-Type": "application/json"
        }

        response = requests.request("POST", url, json=payload, headers=headers)

        print(response.text)

# 输入讯飞开放平台的appid，secret_key和待转写的文件路径
if __name__ == '__main__':
    api = RequestApi(appid="7a7e5c66",
                     secret_key="4013a078ddc20649c3bf44cb1ad41e39",
                     upload_file_path=r"./lfasr_涉政.wav")

    api.get_result()
