# import hashlib
# import http.client
# import json
# import os
# import random
# import time
# import urllib
# from configparser import ConfigParser
#
# from moviepy.editor import VideoFileClip
# from pymongo import MongoClient
#
# import modules.aimodels.packages.iflytek_api as voice_api
#
#
# def get_dict_from_path(_path):
#     """
#     load json dict from json file
#     :param _path:
#     :return:
#     """
#     with open(_path, 'r', encoding='utf-8') as file_data:
#         _dict = json.load(file_data)
#     return _dict
#
#
# def connect_mongodb():
#     """
#     连接mongodb数据库
#     :return:
#     """
#     path = os.path.dirname(os.path.abspath(__file__))
#     MAIN_CONF = path + '/config/gen_scripts_test.cfg'
#     parser = ConfigParser()
#     parser.read(MAIN_CONF)
#     mongodb_host = parser.get('mongodb', 'host')
#     mongodb_db = parser.get('mongodb', 'db')
#     mongodb_port = int(parser.get('mongodb', 'port'))
#     mongodb_user = parser.get('mongodb', 'user')
#     mongodb_password = parser.get('mongodb', 'password')
#     mongodb_authMechanism = parser.get('mongodb', 'authMechanism')
#     client = MongoClient(mongodb_host, username=mongodb_user,
#                          password=mongodb_password,
#                          authSource=mongodb_db,
#                          authMechanism=mongodb_authMechanism,
#                          port=mongodb_port)
#     # client = MongoClient(host='127.0.0.1', port=27017)
#     database = client.get_database(mongodb_db)
#     return database
#
#
# def conversion(data):
#     """
#     数据转换：将json的int类型key转为string类型key
#     :param data:
#     :return:
#     """
#     json_data = json.dumps(data)
#     dict_data = json.loads(json_data)
#     return dict_data
#
#
# def float_to_time(float_data):
#     """
#     格式调整：补足小数点后三位
#     :param float_data:
#     :return:
#     """
#     decimals = str(float_data).split('.')[1]
#     decimals = decimals.ljust(3, '0')
#     data_string = time.strftime('%H:%M:%S',
#                                 time.gmtime(float_data)) + '.' + decimals
#     return data_string
#
#
# def time_to_float(time_str):
#     """
#     格式调整：将时间拆分为数组
#     :param time_str:
#     :return:
#     """
#     data_list = time_str.split(' --> ')
#     time_list = []
#     for data in data_list:
#         data_time = time_to_second(data.split('.')[0]) + float(
#             data.split('.')[1]) / 1000
#         time_list.append(data_time)
#     return time_list[0], time_list[1]
#
#
# def transform(data_lists, write_file):
#     """
#     文件转换：json转换srt
#     :param data_lists:
#     :param write_file:
#     :return:
#     """
#     str_srt = ''
#     for data_list in data_lists:
#         _id = str(data_list["sub_id"]) + '\n'
#         subtitling_time = float_to_time(
#             float(data_list['bg'])) + ' --> ' + float_to_time(
#             float(data_list['ed'])) + '\n'
#         cn = data_list["cn_sub"] + '\n'
#         en = data_list["en_sub"] + '\n'
#         str_srt += _id + subtitling_time + cn + en + '\n'
#     with open(write_file, 'w', encoding='utf-8')as file_data:
#         file_data.write(str_srt)
#     return write_file
#
#
# def trans_eng(_str):
#     """
#     外部翻译接口
#     :param _str:
#     :return:
#     """
#     appid = '20191104000352592'  # 填写你的appid
#     secret_key = 'TDNPbPk4pffxUt3HkMbZ'  # 填写你的密钥
#
#     # httpClient = None
#     myurl = '/api/trans/vip/translate'
#
#     from_lang = 'en'
#     to_lang = 'zh'
#     salt = random.randint(32768, 65536)
#
#     sign = appid + _str + str(salt) + secret_key
#     sign = hashlib.md5(sign.encode()).hexdigest()
#     myurl = myurl + '?appid=' + appid + '&q=' + urllib.parse.quote(
#         _str) + '&from=' + from_lang + '&to=' + to_lang + '&salt=' + str(
#         salt) + '&sign=' + sign
#
#     httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
#     httpClient.request('GET', myurl)
#
#     # response是HTTPResponse对象
#     response = httpClient.getresponse()
#     result_all = response.read().decode("utf-8")
#     result = json.loads(result_all)
#
#     return result['trans_result'][0]['dst']
#
#
# def get_trans(subs_list, lang):
#     """
#     文件处理：输入原始字幕，生成所需要的工具文件
#     :param subs_list:
#     :param lang:
#     :return:
#     """
#
#     full_cn_str = ''
#     char_id_to_time = {}
#     time_to_char_id = {}
#     res_list = []
#
#     for sub_id, sub_value in enumerate(subs_list):
#         if sub_id % round(len(subs_list) / 10) == 0:
#             print('Current Progress:', round(100 * sub_id / len(subs_list), 2),
#                   '%')
#
#         # pprint.pprint(sub_value)
#         raw_bg = sub_value['bg']
#         curr_bg = str(round(int(raw_bg) / 1000, 2))
#
#         raw_ed = sub_value['ed']
#         curr_ed = str(round(int(raw_ed) / 1000, 2))
#
#         curr_sub = sub_value['onebest']
#         # curr_trans = ''
#         if lang == 'en':
#             curr_trans = trans_eng(curr_sub)
#             # print(curr_sub)
#             # print(curr_trans)
#             curr_cn_sub = curr_trans
#             curr_en_sub = curr_sub
#         else:
#             curr_cn_sub = curr_sub
#             curr_en_sub = ''
#
#         res_list.append(
#             {
#                 'sub_id': sub_id,
#                 'bg': curr_bg,
#                 'ed': curr_ed,
#                 'cn_sub': curr_cn_sub,
#                 'en_sub': curr_en_sub,
#             }
#         )
#
#         char_id_to_time[len(full_cn_str)] = curr_bg
#         char_id_to_time[len(full_cn_str) + len(curr_cn_sub) - 1] = curr_ed
#         time_to_char_id[curr_bg] = len(full_cn_str)
#         time_to_char_id[curr_ed] = len(full_cn_str) + len(curr_cn_sub) - 1
#
#         full_cn_str += curr_cn_sub
#
#     return res_list, char_id_to_time, time_to_char_id, full_cn_str
#
#
# def time_to_second(time_data):
#     """
#     格式转换，将时间格式转为秒数
#     :param time_data:
#     :return:
#     """
#     h, m, s = time_data.strip().split(":")
#     return int(h) * 3600 + int(m) * 60 + int(s)
#
#
# def srt_to_ass(srt_path, ass_path):
#     """
#     格式转换，将srt文件转为ass文件
#     :param srt_path:
#     :param ass_path:
#     :return:
#     """
#     compress = "ffmpeg -y -i {} {}".format(srt_path, ass_path)
#     is_run = os.system(compress)
#     if is_run != 0:
#         return ""
#     else:
#         return ass_path
#
#
# def embedded_subtitile(input_path, output_path, sub_path):
#     """
#     嵌入字幕，将字幕文件和mp4合并
#     :param input_path:
#     :param output_path:
#     :param sub_path:
#     :return:
#     """
#     compress = "ffmpeg -i {} -vf subtitles={} {}".format(input_path, sub_path,
#                                                          output_path)
#     is_run = os.system(compress)
#     if is_run != 0:
#         return ""
#     else:
#         return output_path
#
#
# def update_ass(sub_path, style):
#     """
#     编辑字幕格式
#     :param sub_path:
#     :param style:
#     :return:
#     """
#     with open(sub_path, 'r', encoding='utf-8') as file_data:
#         lines = file_data.readlines()
#         for index, value in enumerate(lines):
#             if 'style:' in value.lower():
#                 lines[index] = style
#     with open(sub_path, 'w', encoding='utf-8') as file_data:
#         file_data.writelines(lines)
#     return sub_path
#
#
# class Subtitle:
#     """
#     字幕管理，包含字幕生成，字幕编辑，并将相应数据插入数据库
#     """
#
#     def __init__(self, video_id, suffix='.mp4'):
#         database = connect_mongodb()
#         self.video_collection = database.video
#         self.video_path = self.get_video_path(video_id)
#         self.synthetic_path = 'static/synthetic/' + video_id + suffix
#         self.audio_path = 'static/audios/' + video_id + '.mp3'
#         self.srt_path = 'static/videos/' + video_id + '.srt'
#         self.ass_path = 'static/videos/' + video_id + '.ass'
#
#     def get_video_path(self, video_id):
#         """
#         根据video_id，获取视频url
#         :param video_id:
#         :return:
#         """
#         result = self.video_collection.find_one({'_id': video_id})
#         if result:
#             return result['video_path']
#         return ''
#
#     def generate_audio(self):
#         """
#         根据视频，生成音频
#         :return:
#         """
#         video = VideoFileClip(self.video_path)
#         audio = video.audio
#         audio.write_audiofile(self.audio_path)
#         return self.audio_path
#
#     def generate_subs(self, lang):
#         """
#         根据音频，生成字幕
#         :param lang:
#         :return:
#         """
#         _path = self.audio_path
#         api = voice_api.RequestApi(appid="59b0b177",
#                                    secret_key="a176a32d6f267a72bcd0ffdf73f9f63f",
#                                    upload_file_path=_path, lang=lang)
#         raw_res = api.all_api_request()
#
#         _res = json.loads(raw_res['data'])
#
#         return _res
#
#     def generate_configs(self, video_id, lang='cn'):
#         """
#         生成所有相关文件，并插入数据库
#         :param video_id:
#         :param lang:
#         :return:
#         """
#
#         _path = self.generate_audio()
#         _res = self.generate_subs(lang)
#         res_list, char_id_to_time, time_to_char_id, full_cn_str = get_trans(
#             _res, lang)
#         srt_path = transform(res_list, self.srt_path)
#         ass_path = srt_to_ass(srt_path, self.ass_path)
#         dict_data = conversion(char_id_to_time)
#         _data = {'subtitling': res_list, 'char_id_to_time': dict_data,
#                  'full_cn_str': full_cn_str, 'ass_path': ass_path,
#                  'lang': lang, 'audio_path': self.audio_path}
#         self.video_collection.update_one(
#             {"_id": video_id},
#             {"$set": _data},
#             upsert=True)
#         result = {"video_path": self.video_path, "subtitling": res_list}
#         return result
#
#     def update_configs(self, res_list, video_id, style, lang='first'):
#         """
#         更改字幕，并更新数据库
#         :param res_list:
#         :param video_id:
#         :return:
#         """
#         full_cn_str = ""
#         char_id_to_time = {}
#         for res_dict in res_list:
#             char_id_to_time[len(full_cn_str)] = res_dict['bg']
#             char_id_to_time[len(full_cn_str) + len(res_dict['cn_sub']) - 1] = \
#             res_dict['ed']
#             full_cn_str += res_dict['cn_sub']
#         srt_path = transform(res_list, self.srt_path)
#         ass_path = srt_to_ass(srt_path, self.ass_path)
#         if style:
#             sub_path = update_ass(ass_path, style)
#         else:
#             sub_path = ass_path
#         # video_path = embedded_subtitile(self.video_path, self.synthetic_path, sub_path)
#         dict_data = conversion(char_id_to_time)
#         if lang == 'first':
#             _data = {'subtitling': res_list, 'char_id_to_time': dict_data,
#                      'full_cn_str': full_cn_str, 'ass_path': ass_path}
#         else:
#             _data = {'subtitling': res_list, 'char_id_to_time': dict_data,
#                      'full_cn_str': full_cn_str, 'ass_path': ass_path,
#                      'lang': lang,
#                      'audio_path': self.audio_path}
#         self.video_collection.update_one(
#             {"_id": video_id},
#             {"$set": _data},
#             upsert=True)
#
#     def update_video(self, res_list, video_id, style, lang):
#         """
#         更改视频和字幕，并更新数据库
#         :param res_list:
#         :param video_id:
#         :param lang:
#         :return:
#         """
#         _path = self.generate_audio()
#         self.update_configs(res_list, video_id, style, lang)
#
#
# def main():
#     # 生成字幕
#     # video_id = 'vBluE_demo'
#     # subtitle = Subtitle(video_id)
#     # subtitle.generate_configs(video_id, lang='cn')
#
#     # 编辑字幕
#     video_id = 'e206582d8a01ab56f38c9a94eb054667'
#     subtitle = Subtitle(video_id)
#     # style = "Style: Default,黑体,20,&Hffff00,&H00ffff,&H0,&H0,0,0,0,0,100,100,0,0,1,1,0,4,20,10,10,0\n"
#     # subtitle.generate_audio()
#     subtitle.generate_configs(video_id, lang='en')
#     # subtitle.update_configs(res_list, video_id, style, lang='en')
#
#
# if __name__ == "__main__":
#     main()
#
# # pprint.pprint(_res)


# -*- coding: utf-8 -*-
import json
import time
import random
import hashlib
import urllib
import http.client
import os
from configparser import ConfigParser
from moviepy.editor import VideoFileClip
from pymongo import MongoClient
import modules.aimodels.packages.iflytek_api as voice_api
import fitz
import datetime


def get_dict_from_path(_path):
    """
    load json dict from json file
    :param _path:
    :return:
    """
    with open(_path, 'r', encoding='utf-8') as file_data:
        _dict = json.load(file_data)
    return _dict


def connect_mongodb():
    """
    连接mongodb数据库
    :return:
    """
    path = os.path.dirname(os.path.abspath(__file__))
    MAIN_CONF = path + '/config/gen_scripts_test.cfg'
    parser = ConfigParser()
    parser.read(MAIN_CONF)
    mongodb_host = parser.get('mongodb', 'host')
    mongodb_db = parser.get('mongodb', 'db')
    mongodb_user = parser.get('mongodb', 'user')
    mongodb_password = parser.get('mongodb', 'password')
    mongodb_authMechanism = parser.get('mongodb', 'authMechanism')
    mongodb_port = int(parser.get('mongodb', 'port'))
    client = MongoClient(host=mongodb_host, username=mongodb_user, password=mongodb_password,
                         authSource=mongodb_db, authMechanism=mongodb_authMechanism, port=mongodb_port)
    database = client.get_database(mongodb_db)
    return database


def conversion(data):
    """
    数据转换：将json的int类型key转为string类型key
    :param data:
    :return:
    """
    json_data = json.dumps(data)
    dict_data = json.loads(json_data)
    return dict_data


def float_to_time(float_data):
    """
    格式调整：补足小数点后三位
    :param float_data:
    :return:
    """
    decimals = str(float_data).split('.')[1]
    decimals = decimals.ljust(3, '0')
    data_string = time.strftime('%H:%M:%S', time.gmtime(float_data)) + '.' + decimals
    return data_string


def time_to_float(time_str):
    """
    格式调整：将时间拆分为数组
    :param time_str:
    :return:
    """
    data_list = time_str.split(' --> ')
    time_list = []
    for data in data_list:
        data_time = time_to_second(data.split('.')[0]) + float(data.split('.')[1]) / 1000
        time_list.append(data_time)
    return time_list[0], time_list[1]


def transform(data_lists, write_file):
    """
    文件转换：json转换srt
    :param data_lists:
    :param write_file:
    :return:
    """
    str_srt = ''
    for data_list in data_lists:
        _id = str(data_list["sub_id"]) + '\n'
        subtitling_time = float_to_time(float(data_list['bg'])) + ' --> ' + float_to_time(
            float(data_list['ed'])) + '\n'
        cn = data_list["cn_sub"] + '\n'
        en = data_list["en_sub"] + '\n'
        str_srt += _id + subtitling_time + cn + en + '\n'
    with open(write_file, 'w', encoding='utf-8')as file_data:
        file_data.write(str_srt)
    return write_file


def trans_eng(_str):
    """
    外部翻译接口
    :param _str:
    :return:
    """
    appid = '20191104000352592'  # 填写你的appid
    secret_key = 'TDNPbPk4pffxUt3HkMbZ'  # 填写你的密钥

    # httpClient = None
    myurl = '/api/trans/vip/translate'

    from_lang = 'en'
    to_lang = 'zh'
    salt = random.randint(32768, 65536)

    sign = appid + _str + str(salt) + secret_key
    sign = hashlib.md5(sign.encode()).hexdigest()
    myurl = myurl + '?appid=' + appid + '&q=' + urllib.parse.quote(
        _str) + '&from=' + from_lang + '&to=' + to_lang + '&salt=' + str(salt) + '&sign=' + sign

    httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
    httpClient.request('GET', myurl)

    # response是HTTPResponse对象
    response = httpClient.getresponse()
    result_all = response.read().decode("utf-8")
    result = json.loads(result_all)

    return result['trans_result'][0]['dst']


def get_trans(subs_list, lang):
    """
    文件处理：输入原始字幕，生成所需要的工具文件
    :param subs_list:
    :param lang:
    :return:
    """

    full_cn_str = ''
    char_id_to_time = {}
    time_to_char_id = {}
    res_list = []

    for sub_id, sub_value in enumerate(subs_list):
        if sub_id % round(len(subs_list) / 10) == 0:
            print('Current Progress:', round(100 * sub_id / len(subs_list), 2), '%')

        # pprint.pprint(sub_value)
        raw_bg = sub_value['bg']
        curr_bg = str(round(int(raw_bg) / 1000, 2))

        raw_ed = sub_value['ed']
        curr_ed = str(round(int(raw_ed) / 1000, 2))

        curr_sub = sub_value['onebest']
        # curr_trans = ''
        if lang == 'en':
            curr_trans = trans_eng(curr_sub)
            # print(curr_sub)
            # print(curr_trans)
            curr_cn_sub = curr_trans
            curr_en_sub = curr_sub
        else:
            curr_cn_sub = curr_sub
            curr_en_sub = ''

        res_list.append(
            {
                'sub_id': sub_id,
                'bg': curr_bg,
                'ed': curr_ed,
                'cn_sub': curr_cn_sub,
                'en_sub': curr_en_sub,
            }
        )

        char_id_to_time[len(full_cn_str)] = curr_bg
        char_id_to_time[len(full_cn_str) + len(curr_cn_sub) - 1] = curr_ed
        time_to_char_id[curr_bg] = len(full_cn_str)
        time_to_char_id[curr_ed] = len(full_cn_str) + len(curr_cn_sub) - 1

        full_cn_str += curr_cn_sub

    return res_list, char_id_to_time, time_to_char_id, full_cn_str


def time_to_second(time_data):
    """
    格式转换，将时间格式转为秒数
    :param time_data:
    :return:
    """
    h, m, s = time_data.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def srt_to_ass(srt_path, ass_path):
    """
    格式转换，将srt文件转为ass文件
    :param srt_path:
    :param ass_path:
    :return:
    """
    compress = "ffmpeg -i {} {}".format(srt_path, ass_path)
    is_run = os.system(compress)
    if is_run != 0:
        return ""
    else:
        return ass_path


def update_ass(sub_path, style):
    """
    编辑字幕格式
    :param sub_path:
    :param style:
    :return:
    """
    with open(sub_path, 'r', encoding='utf-8') as file_data:
        lines = file_data.readlines()
        for index, value in enumerate(lines):
            if 'style:' in value.lower():
                lines[index] = style
    with open(sub_path, 'w', encoding='utf-8') as file_data:
        file_data.writelines(lines)
    return sub_path


def pdf_to_dict(_path):
    res_dict = {}
    doc = fitz.open(_path)
    for page_id in range(doc.pageCount):
        curr_page = doc.loadPage(page_id)
        page_content = curr_page.getText("text")
        res_dict[page_id] = page_content.split('\n')

    return res_dict


def dict_to_str_and_map(pdf_dict):
    full_str = ''
    charId_to_pageId = []
    for page_id in pdf_dict:
        content_list = pdf_dict[page_id]
        charId_to_pageId.append([len(full_str), page_id + 1])
        page_str = ''.join(content_list)
        full_str += page_str

    charId_to_pageId.append([len(full_str) + 1, len(pdf_dict) + 1])

    return full_str, charId_to_pageId


def load_database(pdfIds_list):
    res_dict = {}
    map_dict = {}
    for pdfId in pdfIds_list:
        curr_content = get_dict_from_path('pdf_database/ ' + pdfId + '.json')
        full_str = curr_content['full_str']
        charId_to_pageId = curr_content['config']['charId_to_pageId']

        res_dict[pdfId] = full_str
        map_dict[pdfId] = charId_to_pageId

    return res_dict, map_dict


def generate_pdf_picture(file_path, image_path):
    doc = fitz.open(file_path)
    count_page = doc.pageCount
    if count_page > 1:
        page = doc[0]
        rotate = int(0)
        zoom_x = 2.0
        zoom_y = 2.0
        trans = fitz.Matrix(zoom_x, zoom_y).preRotate(rotate)
        pm = page.getPixmap(matrix=trans, alpha=False)
        pm.writePNG(image_path)
        print("运行完成")
        return True
    else:
        print("此文档无内容，跳出")
        return False


class Document:
    def __init__(self):
        database = connect_mongodb()
        self.document_collection = database.document

    def save_str_to_database(self, file_id, file_name, file_path, image_path, price, video_id):
        """
        生成预览图，并插入数据库
        :param file_id:
        :param file_name:
        :param file_path:
        :param image_path:
        :param price:
        :param video_id:
        :return:
        """
        full_str, char_id_to_page_id = dict_to_str_and_map(pdf_to_dict(file_path))
        flag = generate_pdf_picture(file_path, image_path)
        if flag:
            document_dict = {
                '_id': file_id,
                'file_name': file_name,
                'file_path': file_path,
                'image_path': image_path,
                'price': price,
                'video_id': video_id,
                'time': time.time(),
                'type': file_path.lower().split('.')[-1],
                'full_str': full_str,
                'char_id_to_page_id': char_id_to_page_id,
                'download_counts': 0
            }
            self.document_collection.insert_one(document_dict)
            return flag
        else:
            return flag


def embedded_subtitle(input_path, output_path, sub_path):
    """
    嵌入字幕，将字幕文件和mp4合并
    :param input_path:
    :param output_path:
    :param sub_path:
    :return:
    """
    compress = "ffmpeg -i {} -vf subtitles={} {}".format(input_path, sub_path, output_path)
    is_run = os.system(compress)
    if is_run != 0:
        return ""
    else:
        return output_path


class Subtitle:
    """
    字幕管理，包含字幕生成，字幕编辑，并将相应数据插入数据库
    """

    def __init__(self, video_id, suffix='.mp4'):
        database = connect_mongodb()
        self.video_collection = database.video
        self.video_path = self.get_video_path(video_id)
        self.synthetic_path = 'static/synthetic/' + video_id + suffix
        self.audio_path = 'static/audios/' + video_id + '.mp3'
        self.srt_path = 'static/videos/' + video_id + '.srt'
        self.ass_path = 'static/videos/' + video_id + '.ass'

    def get_video_path(self, video_id):
        """
        根据video_id，获取视频url
        :param video_id:
        :return:
        """
        result = self.video_collection.find_one({'_id': video_id})
        if result:
            return result['video_path']
        return ''

    def generate_audio(self):
        """
        根据视频，生成音频
        :return:
        """
        video = VideoFileClip(self.video_path)
        audio = video.audio
        audio.write_audiofile(self.audio_path)
        return self.audio_path

    def generate_subs(self, lang):
        """
        根据音频，生成字幕
        :param lang:
        :return:
        """
        _path = self.audio_path
        api = voice_api.RequestApi(appid="59b0b177", secret_key="a176a32d6f267a72bcd0ffdf73f9f63f",
                                   upload_file_path=_path, lang=lang)
        raw_res = api.all_api_request()

        _res = json.loads(raw_res['data'])

        return _res

    def generate_configs(self, video_id, lang='cn'):
        """
        生成所有相关文件，并插入数据库
        :param video_id:
        :param lang:
        :return:
        """
        _path = self.generate_audio()
        _res = self.generate_subs(lang)
        res_list, char_id_to_time, time_to_char_id, full_cn_str = get_trans(_res, lang)
        srt_path = transform(res_list, self.srt_path)
        ass_path = srt_to_ass(srt_path, self.ass_path)
        dict_data = conversion(char_id_to_time)
        _data = {'subtitling': res_list, 'char_id_to_time': dict_data,
                 'full_cn_str': full_cn_str, 'ass_path': ass_path,
                 'lang': lang, 'audio_path': self.audio_path}
        self.video_collection.update_one(
            {"_id": video_id},
            {"$set": _data},
            upsert=True)
        result = {"video_path": self.video_path, "subtitling": res_list}
        return result

    def update_configs(self, res_list, video_id, style, lang='first'):
        """
        更改字幕，并更新数据库
        :param lang:
        :param style:
        :param res_list:
        :param video_id:
        :return:
        """
        full_cn_str = ""
        char_id_to_time = {}
        for res_dict in res_list:
            char_id_to_time[len(full_cn_str)] = res_dict['bg']
            char_id_to_time[len(full_cn_str) + len(res_dict['cn_sub']) - 1] = res_dict['ed']
            full_cn_str += res_dict['cn_sub']
        srt_path = transform(res_list, self.srt_path)
        ass_path = srt_to_ass(srt_path, self.ass_path)
        if style:
            sub_path = update_ass(ass_path, style)
        else:
            sub_path = ass_path
        # video_path = embedded_subtitile(self.video_path, self.synthetic_path, sub_path)
        dict_data = conversion(char_id_to_time)
        if lang == 'first':
            _data = {'subtitling': res_list, 'char_id_to_time': dict_data,
                     'full_cn_str': full_cn_str, 'ass_path': ass_path}
        else:
            _data = {'subtitling': res_list, 'char_id_to_time': dict_data,
                     'full_cn_str': full_cn_str, 'ass_path': ass_path, 'lang': lang,
                     'audio_path': self.audio_path}
        self.video_collection.update_one(
            {"_id": video_id},
            {"$set": _data},
            upsert=True)

    def update_video(self, res_list, video_id, style, lang):
        """
        更改视频和字幕，并更新数据库
        :param style:
        :param res_list:
        :param video_id:
        :param lang:
        :return:
        """
        _path = self.generate_audio()
        self.update_configs(res_list, video_id, style, lang)


def main():
    # 生成字幕
    # video_id = 'vBluE_demo'
    # subtitle = Subtitle(video_id)
    # subtitle.generate_configs(video_id, lang='cn')

    # 编辑字幕
    # video_id = 'AI_V7_1'
    # subtitle = Subtitle(video_id)
    # style = "Style: Default,黑体,20,&Hffff00,&H00ffff,&H0,&H0,0,0,0,0,100,100,0,0,1,1,0,4,20,10,10,0\n"
    # subtitle.generate_audio()
    # subtitle.generate_configs(video_id, lang='en')
    # subtitle.update_configs(res_list, video_id, style, lang='en')

    document = Document()
    file_id = 'test03'
    file_name = '重力'
    file_path = './static/document/重力.pdf'
    image_path = './static/image/重力.png'
    price = 10.00
    video_id = '0293f09cab3a46af845e83ca29dfb033'
    flag = document.save_str_to_database(file_id, file_name, file_path, image_path, price, video_id)
    print(flag)


if __name__ == "__main__":
    main()

# pprint.pprint(_res)

