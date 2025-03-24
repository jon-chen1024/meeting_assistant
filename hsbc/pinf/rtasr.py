# -*- encoding:utf-8 -*-
import hashlib
import hmac
import base64
from socket import *
import json, time, threading
from websocket import create_connection
import websocket
from urllib.parse import quote
import logging

# reload(sys)
# sys.setdefaultencoding("utf8")
class Client():
    def __init__(self):
        base_url = "wss://rtasr.xfyun.cn/v1/ws"
        self.end_text = ""
        ts = str(int(time.time()))
        tt = (app_id + ts).encode('utf-8')
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding='utf-8')

        apiKey = api_key.encode('utf-8')
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        self.end_tag = "{\"end\": true}"

        self.ws = create_connection(base_url + "?appid=" + app_id + "&ts=" + ts + "&signa=" + quote(signa))
        self.trecv = threading.Thread(target=self.recv)
        self.trecv.start()

    def send(self, file_path):
        file_object = open(file_path, 'rb')
        try:
            index = 1
            while True:
                chunk = file_object.read(1280)
                if not chunk:
                    break
                self.ws.send(chunk)

                index += 1
                time.sleep(0.04)
        finally:
            file_object.close()

        self.ws.send(bytes(self.end_tag.encode('utf-8')))
        print("send end tag success")

    def recv(self):
        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    print("receive result end")
                    break
                result_dict = json.loads(result)
                # 解析结果
                if result_dict["action"] == "started":
                    print("handshake success, result: " + result)

                if result_dict["action"] == "result":
                    result_1 = result_dict
                    # result_2 = json.loads(result_1["cn"])
                    # result_3 = json.loads(result_2["st"])
                    # result_4 = json.loads(result_3["rt"])
                    print("rtasr result: " + result_1["data"])
                    # 调用示例
                    self.analysis_result(result_1["data"])

                if result_dict["action"] == "error":
                    print("rtasr error: " + result)

                    self.ws.close()
                    return
            print("end_text:" + self.end_text)
        except websocket.WebSocketConnectionClosedException:
            print("receive result end")


    def analysis_result(self,data):
        """
        获取识别并返回字符串。

        :param data: 所获取的识别的Json字符串
        :return: None，但会更新全局变量 `_text` 和 `endText`
        """
        # 解析 JSON 数据
        result = json.loads(data)

        # 使用列表推导式提取有用的字段
        words = [item['cw'][0]['w'] for item in result['cn']['st']['rt'][0]['ws']]

        # 将提取的单词连接成一句话
        testing = ''.join(words)

        _this_type = result['cn']['st']['type']
        if _this_type == "0":
            self.end_text += testing

    def close(self):
        self.ws.close()
        print("connection closed")


if __name__ == '__main__':
    logging.basicConfig()

    app_id = "7a7e5c66"
    api_key = "0b032c43ad6cbd4f80122bf9ffb16866"
    file_path = r"./test_1.pcm"

    client = Client()
    client.send(file_path)