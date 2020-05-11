# # import json
# # import os
# # from configparser import ConfigParser
# #
# # import requests
# # from pymongo import MongoClient, ReadPreference
# #
# #
# # class Search:
# #     def __init__(self):
# #         database = connect_mongodb()
# #         self.video_collection = database.video
# #
# #     def video_search(self, query_str, video_ids, mode='global', isBluE=True,
# #                      isSemantic=True):
# #
# #         result_data = []
# #         match_frame = {}
# #         match_ids = []
# #         if mode == 'global':
# #             if not video_ids:
# #                 results = self.video_collection.find({"state": 2}, {"_id": 1})
# #                 for result in results:
# #                     video_ids.append(result["_id"])
# #             if query_str:
# #                 res_dict = self.global_search(query_str, video_ids,
# #                                               isBluE=isBluE)
# #                 for video_id in res_dict:
# #                     char_dur, time_dur = self.result_transformer(video_id,
# #                                                                  res_dict[
# #                                                                      video_id][
# #                                                                      'pos'])
# #                     match_frame[video_id] = {
# #                         "matched_sub": res_dict[video_id]['matched_str'],
# #                         "start_time": time_dur[0],
# #                         "end_time": time_dur[1],
# #                         "subs_pos": char_dur,
# #                         "video_id": video_id}
# #                     match_ids.append(video_id)
# #             else:
# #                 match_ids.extend(video_ids)
# #             if match_ids:
# #                 results = self.video_collection.find(
# #                     {"_id": {"$in": match_ids}, "state": 2})
# #                 for result in results:
# #                     dict_search = {}
# #                     dict_search['video_id'] = result['_id']
# #                     dict_search['title'] = result['title']
# #                     dict_search['video_path'] = {"720P": result['video_path']}
# #                     dict_search['audio_path'] = result['audio_path']
# #                     dict_search['lang'] = result['lang']
# #                     dict_search['subtitling'] = result['subtitling']
# #                     dict_search['upload_date'] = result['date']
# #                     dict_search['category'] = result['category']
# #                     # dict_search['image_path'] = result['image_path']
# #                     # dict_search['webvtt'] = result['webvtt']
# #                     if query_str:
# #                         dict_search['match_frame'] = match_frame[result['_id']]
# #                     result_data.append(dict_search)
# #         if mode == 'local':
# #             res_dict = self.local_search(query_str, video_ids[0],
# #                                          isSemantic=isSemantic)
# #             for video_id in res_dict:
# #                 char_dur, time_dur = self.result_transformer(video_id,
# #                                                              res_dict[video_id][
# #                                                                  'pos'])
# #                 match_frame = {
# #                     "matched_sub": res_dict[video_id]['matched_str'],
# #                     "start_time": time_dur[0],
# #                     "end_time": time_dur[1],
# #                     "subs_pos": char_dur,
# #                     "video_id": video_id}
# #             dict_search = {}
# #             dict_search['match_frame'] = match_frame
# #             result_data.append(dict_search)
# #
# #         return result_data
# #
# #     def global_search(self, query_str, video_ids, isBluE=False):
# #
# #         inputs_dict = self.get_input_dict(video_ids)
# #
# #         res_dict = {}
# #         if not isBluE:
# #             for video_id in inputs_dict:
# #                 curr_str = inputs_dict[video_id]
# #                 if query_str in curr_str:
# #                     matched_index = curr_str.index(query_str)
# #                     res_dict[video_id] = {
# #                         'pos': [matched_index,
# #                                 matched_index + len(query_str) + 1],
# #                         'matched_str': query_str
# #                     }
# #
# #         if isBluE:
# #             bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
# #                                               isSemantic=0,
# #                                               max_size=100)
# #             for item in bluE_results:
# #                 curr_key = item['key_id']
# #                 str_pos = item['str_position']
# #                 if curr_key not in res_dict:
# #                     res_dict[curr_key] = {
# #                         'pos': str_pos,
# #                         'matched_str': item['matched_str']
# #                     }
# #
# #         return res_dict
# #
# #     def get_input_dict(self, video_ids):
# #
# #         res_dict = {}
# #         if video_ids:
# #             results = self.video_collection.find(
# #                 {"_id": {"$in": video_ids}, "state": 2},
# #                 {"full_cn_str": 1, "_id": 1})
# #         else:
# #             results = self.video_collection.find({"state": 2},
# #                                                  {"full_cn_str": 1, "_id": 1})
# #         for result in results:
# #             res_dict[result["_id"]] = result["full_cn_str"]
# #         return res_dict
# #
# #     def bluE_standard(self, query_str, input_paragraph, lang='ch', isSemantic=0,
# #                       max_size=10):
# #
# #         _url = 'http://codes.haetek.com:6675/blue'
# #         _data = {
# #             "dbmodelname": "blue",
# #             "modelaction": "search",
# #             "extradata": {
# #                 "querystring": query_str,
# #                 "paragraph": input_paragraph,
# #                 "lang": lang,
# #                 "issemantic": isSemantic,
# #                 "isjson": True
# #             },
# #             "modeltype": "ai"
# #         }
# #         res = requests.post(url=_url, json=_data)
# #         res = json.loads(res.text)['resultdata']
# #         raw_res = res[1:max_size + 1]
# #
# #         return raw_res
# #
# #     def local_search(self, query_str, video_id, isSemantic=True):
# #
# #         res_dict = {}
# #         inputs_dict = self.get_input_dict([video_id])
# #         bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
# #                                           isSemantic=isSemantic,
# #                                           max_size=10)
# #
# #         for item in bluE_results:
# #             curr_key = item['key_id']
# #             str_pos = item['str_position']
# #             # toDo generating multiple results
# #             if curr_key not in res_dict:
# #                 res_dict[curr_key] = {
# #                     'pos': str_pos,
# #                     'matched_str': item['matched_str']
# #                 }
# #
# #         return res_dict
# #
# #     def result_transformer(self, video_id, res_pos):
# #
# #         res_charId_bg = int(res_pos[0])
# #         res_charId_ed = int(res_pos[1])
# #
# #         result = self.video_collection.find_one({"_id": video_id},
# #                                                 {"char_id_to_time": 1})
# #
# #         charId_to_time = result["char_id_to_time"]
# #
# #         extrinsic_char_bg = 0
# #         extrinsic_char_ed = 0
# #
# #         for raw_char_id in charId_to_time:
# #             char_id = int(raw_char_id)
# #             if char_id <= res_charId_bg:
# #                 if char_id > extrinsic_char_bg or extrinsic_char_bg == 0:
# #                     extrinsic_char_bg = char_id
# #
# #             if char_id >= res_charId_ed:
# #                 if char_id < extrinsic_char_ed or extrinsic_char_ed == 0:
# #                     extrinsic_char_ed = char_id
# #
# #         extrinsic_time_bg = charId_to_time[str(extrinsic_char_bg)]
# #         extrinsic_time_ed = charId_to_time[str(extrinsic_char_ed)]
# #
# #         return [extrinsic_char_bg, extrinsic_char_ed], [extrinsic_time_bg,
# #                                                         extrinsic_time_ed]
# #
# #
# # def connect_mongodb():
# #     '''
# #
# #     :return:
# #     '''
# #     path = os.path.dirname(os.path.abspath(__file__))
# #     MAIN_CONF = path + '/config/gen_scripts_test.cfg'
# #     parser = ConfigParser()
# #     parser.read(MAIN_CONF)
# #     mongodb_host = parser.get('mongodb', 'host')
# #     mongodb_db = parser.get('mongodb', 'db')
# #     mongodb_port = int(parser.get('mongodb', 'port'))
# #     mongodb_user = parser.get('mongodb', 'user')
# #     mongodb_password = parser.get('mongodb', 'password')
# #     mongodb_authMechanism = parser.get('mongodb', 'authMechanism')
# #     client = MongoClient(mongodb_host, username=mongodb_user,
# #                          password=mongodb_password,
# #                          authSource=mongodb_db,
# #                          authMechanism=mongodb_authMechanism,
# #                          read_preference=ReadPreference.SECONDARY_PREFERRED,
# #                          port=mongodb_port)
# #     # client = MongoClient(host='127.0.0.1', port=27017)
# #     database = client.get_database(mongodb_db)
# #     return database
#
#
# # -*- coding: utf-8 -*-
# #
#
#
# import json
# import os
# import pprint
# import time
# from configparser import ConfigParser
#
# import requests
# from pymongo import MongoClient
#
#
# class Search:
#     def __init__(self):
#         database = connect_mongodb()
#         self.video_collection = database.video
#
#     def video_search(self, query_str, video_ids, mode='global', isBluE=True,
#                      isSemantic=True):
#         match_ids = []
#         result_data = []
#         match_frame = {}
#         match_frames = []
#         if mode == 'global':
#             if not video_ids:
#                 results = self.video_collection.find({"state": 2}, {"_id": 1})
#                 for result in results:
#                     video_ids.append(result["_id"])
#             if query_str:
#                 print('Video Size: ', video_ids)
#                 res_dict = self.global_search(query_str, video_ids,
#                                               isBluE=isBluE)
#                 # print('res_dict: ',res_dict)
#                 for video_id in res_dict:
#                     result = self.video_collection.find_one({"_id": video_id},
#                                                             {"_id": 1,
#                                                              "full_cn_str": 1})
#                     full_cn_str = result['full_cn_str']
#                     if res_dict[video_id]["type"] == "subtitle":
#                         char_dur, time_dur = self.result_transformer(video_id,
#                                                                      res_dict[
#                                                                          video_id][
#                                                                          'pos'])
#                         match_frame[video_id] = {
#                             "matched_str": res_dict[video_id]['matched_str'],
#                             "start_time": time_dur[0],
#                             "end_time": time_dur[1],
#                             "subs_pos": char_dur,
#                             "whole_str": full_cn_str[
#                                          char_dur[0]:char_dur[1] + 1],
#                             "video_id": video_id,
#                             "type": "subtitle"}
#                     else:
#                         match_frame[video_id] = {
#                             "matched_str": res_dict[video_id]['matched_str'],
#                             "video_id": video_id,
#                             "type": res_dict[video_id]["type"]
#                         }
#                     match_ids.append(video_id)
#             else:
#                 match_ids.extend(video_ids)
#             if match_ids:
#                 results = self.video_collection.find(
#                     {"_id": {"$in": match_ids}, "state": 2})
#                 for result in results:
#                     dict_search = {}
#                     dict_search['video_id'] = result['_id']
#                     dict_search['title'] = result['title']
#                     dict_search['user_id'] = result['user_id']
#                     dict_search['category'] = result['category']
#                     # dict_search['video_path'] = {"720P":result['video_path']}
#                     # dict_search['audio_path'] = result['audio_path']
#                     dict_search['lang'] = result['lang']
#                     # dict_search['subtitling'] = result['subtitling']
#                     dict_search['upload_date'] = result['upload_time']
#                     dict_search['image_path'] = result['image_path']
#                     # dict_search['webvtt'] = result['webvtt']
#                     if query_str:
#                         dict_search['match_frame'] = match_frame[result['_id']]
#                     result_data.append(dict_search)
#         if mode == 'local':
#             res_dict = self.local_search(query_str, video_ids[0],
#                                          isSemantic=isSemantic)
#             result = self.video_collection.find_one({"_id": video_ids[0]},
#                                                     {"video_path": 1, "_id": 1,
#                                                      "full_cn_str": 1})
#             video_path = result['video_path']
#             full_cn_str = result['full_cn_str']
#             for _num in res_dict:
#                 video_id = res_dict[_num]['video_id']
#                 pos = res_dict[_num]['pos']
#                 char_dur, time_dur = self.result_transformer(video_id, pos)
#                 # time = time_format(float(time_dur[0]))
#                 # mobile = '15642336090'
#                 # output_directory = './static/picture/' + mobile + '_' + video_id
#                 # if not os.path.exists(output_directory):
#                 #     os.makedirs(output_directory)
#                 # output_path = output_directory + '/' + str(_num) + '.jpg'
#                 # image_path = generate_picture(video_path, output_path, time)
#                 match_frame = {
#                     "matched_str": res_dict[_num]['matched_str'],
#                     "start_time": time_dur[0],
#                     "end_time": time_dur[1],
#                     "subs_pos": char_dur,
#                     "whole_str": full_cn_str[char_dur[0]:char_dur[1] + 1],
#                     # "image_path": image_path,
#                     "video_id": video_id}
#                 match_frames.append(match_frame)
#             dict_search = {}
#             dict_search['match_frame'] = match_frames
#             result_data.append(dict_search)
#
#         return result_data
#
#     def global_search(self, query_str, video_ids, isBluE=False):
#
#         inputs_dict = self.get_global_input_dict(video_ids)
#         # print("inputs_dict:",inputs_dict)
#         res_dict = {}
#         if not isBluE:
#             for video_id in inputs_dict:
#                 curr_str = inputs_dict[video_id]
#                 if query_str in curr_str:
#                     matched_index = curr_str.index(query_str)
#                     res_dict[video_id] = {
#                         'pos': [matched_index,
#                                 matched_index + len(query_str) + 1],
#                         'matched_str': query_str
#                     }
#
#         if isBluE:
#             bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
#                                               isSemantic=0, max_size=100)
#             for item in bluE_results:
#                 curr_key = item['key_id']
#                 str_pos = item['str_position']
#                 if curr_key not in res_dict:
#                     res_dict[curr_key] = {
#                         'pos': str_pos,
#                         'matched_str': item['matched_str'],
#                         'type': "subtitle"
#                     }
#             des_dict = res_dict.copy()
#             for key in des_dict:
#                 if "description" in key:
#                     new_key = key.split('_')[1]
#                     des_dict[new_key] = res_dict[key]
#                     des_dict[new_key]["type"] = "description"
#                     des_dict.pop(key)
#             title_dict = des_dict.copy()
#             for key in title_dict:
#                 if "title" in key:
#                     new_key = key.split('_')[1]
#                     title_dict[new_key] = des_dict[key]
#                     title_dict[new_key]["type"] = "title"
#                     title_dict.pop(key)
#         return title_dict
#
#     def get_input_dict(self, video_ids):
#
#         res_dict = {}
#         if video_ids:
#             results = self.video_collection.find(
#                 {"_id": {"$in": video_ids}, "state": 2},
#                 {"full_cn_str": 1, "_id": 1})
#         else:
#             results = self.video_collection.find({"state": 2},
#                                                  {"full_cn_str": 1, "_id": 1})
#         for result in results:
#             res_dict[result["_id"]] = result["full_cn_str"]
#         return res_dict
#
#     def get_global_input_dict(self, video_ids):
#
#         res_dict = {}
#         if video_ids:
#             results = self.video_collection.find(
#                 {"_id": {"$in": video_ids}, "state": 2},
#                 {"full_cn_str": 1, "_id": 1, "title": 1, "description": 1})
#         else:
#             results = self.video_collection.find({"state": 2},
#                                                  {"full_cn_str": 1, "_id": 1,
#                                                   "title": 1, "description": 1})
#         for result in results:
#             key = result["_id"]
#             res_dict[key] = result["full_cn_str"]
#             if "title" in result and result["title"]:
#                 res_dict["title_" + key] = result["title"]
#             if "description" in result and result["description"]:
#                 res_dict["description_" + key] = result["description"]
#         return res_dict
#
#     def bluE_standard(self, query_str, input_paragraph, lang='ch', isSemantic=0,
#                       max_size=10):
#
#         _url = 'http://codes.haetek.com:6675/blue'
#         _data = {
#             "dbmodelname": "blue",
#             "modelaction": "search",
#             "extradata": {
#                 "querystring": query_str,
#                 "paragraph": input_paragraph,
#                 "lang": lang,
#                 "issemantic": isSemantic,
#                 "isjson": True
#             },
#             "modeltype": "ai"
#         }
#         res = requests.post(url=_url, json=_data)
#         res = json.loads(res.text)['resultdata']
#         raw_res = res[1:max_size + 1]
#
#         return raw_res
#
#     def local_search(self, query_str, video_id, isSemantic=True):
#
#         res_dict = {}
#         curr_key = 0
#         inputs_dict = self.get_input_dict([video_id])
#         bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
#                                           isSemantic=isSemantic, max_size=10)
#         for item in bluE_results:
#             video_id = item['key_id']
#             str_pos = item['str_position']
#             # toDo generating multiple results
#             if curr_key < 10:
#                 res_dict[curr_key] = {
#                     'video_id': video_id,
#                     'pos': str_pos,
#                     'matched_str': item['matched_str']
#                 }
#                 curr_key += 1
#
#         return res_dict
#
#     def result_transformer(self, video_id, res_pos):
#
#         res_charId_bg = int(res_pos[0])
#         res_charId_ed = int(res_pos[1])
#
#         result = self.video_collection.find_one({"_id": video_id},
#                                                 {"char_id_to_time": 1})
#
#         charId_to_time = result["char_id_to_time"]
#
#         extrinsic_char_bg = 0
#         extrinsic_char_ed = 0
#
#         for raw_char_id in charId_to_time:
#             char_id = int(raw_char_id)
#             if char_id <= res_charId_bg:
#                 if char_id > extrinsic_char_bg or extrinsic_char_bg == 0:
#                     extrinsic_char_bg = char_id
#
#             if char_id >= res_charId_ed:
#                 if char_id < extrinsic_char_ed or extrinsic_char_ed == 0:
#                     extrinsic_char_ed = char_id
#
#         extrinsic_time_bg = charId_to_time[str(extrinsic_char_bg)]
#         extrinsic_time_ed = charId_to_time[str(extrinsic_char_ed)]
#
#         return [extrinsic_char_bg, extrinsic_char_ed], [extrinsic_time_bg,
#                                                         extrinsic_time_ed]
#
#
# def connect_mongodb():
#     '''
#
#     :return:
#     '''
#     path = os.path.dirname(os.path.abspath(__file__))
#     MAIN_CONF = path + '/config/gen_scripts_test.cfg'
#     parser = ConfigParser()
#     parser.read(MAIN_CONF)
#     mongodb_host = parser.get('mongodb', 'host')
#     mongodb_db = parser.get('mongodb', 'db')
#     mongodb_user = parser.get('mongodb', 'user')
#     mongodb_password = parser.get('mongodb', 'password')
#     mongodb_authMechanism = parser.get('mongodb', 'authMechanism')
#     mongodb_port = int(parser.get('mongodb', 'port'))
#     client = MongoClient(host=mongodb_host, username=mongodb_user,
#                          password=mongodb_password,
#                          authSource=mongodb_db,
#                          authMechanism=mongodb_authMechanism, port=mongodb_port)
#     # client = MongoClient(host='127.0.0.1', port=27017)
#     database = client.get_database(mongodb_db)
#     return database
#
#
# def main():
#     print('Start')
#     print()
#     ###### Sample One (Local Search) ######
#
#     # video_ids = ['unique_id2']
#     # query_str = '弦理论如何描述基本粒子'
#     # query_str = '空调'
#     video_ids = ['b47f7dd5c45c9839e2b6f56dcb300239']
#     query_str = '宇宙的维度'
#
#     ss = time.time()
#     s = Search()
#     res_list = s.video_search(query_str, video_ids, mode='local')
#
#     ee = time.time()
#
#     print('###### Sample One (Local Search) ######')
#     print('Query:', query_str)
#     pprint.pprint(res_list)
#     print('Video Size:', len(video_ids))
#     print('Time Cost: ', ee - ss)
#     print()
#
#     ###### Sample Two (Global Search) ######
#
#     # video_ids = ['unique_id1','unique_id2','unique_id5','unique_id7']
#     # video_ids = []
#     # query_str = '傅立叶变换逆运算'
#
#     # ss = time.time()
#     # s = Search()
#     # res_list = s.video_search(query_str, video_ids, mode='global')
#
#     # ee = time.time()
#
#     # print('###### Sample Two (Global Search) ######')
#     # print('Query:',query_str)
#     # pprint.pprint(res_list)
#     # print('Video Size:',len(video_ids))
#     # print('Time Cost: ', ee-ss)
#
#
# if __name__ == "__main__":
#     main()


# -*- coding: utf-8 -*-
#


import json
import os
import time
import pprint
import random
import string
import hashlib
import urllib
import requests
import http.client
from configparser import ConfigParser
from pymongo import MongoClient, ReadPreference


# def generate_picture(input_path, output_path, time):

#     compress = "ffmpeg -i {} -y -f image2 -ss {} -vframes 1 {}".format(input_path, time, output_path)
#     is_run = os.system(compress)
#     if is_run != 0:
#         return ''
#     else:
#         return output_path

# def time_format(float_data):

#     data_string = time.strftime('%H:%M:%S', time.gmtime(float_data))
#     return data_string


class Search:
    def __init__(self):
        database = connect_mongodb()
        self.video_collection = database.video

    def video_search(self, query_str, video_ids, mode='global', isBluE=True,
                     isSemantic=True):

        result_data = []
        match_frame = {}
        match_frames = []
        match_ids = []
        if mode == 'global':
            if not video_ids:
                results = self.video_collection.find({"state": 2}, {"_id": 1})
                for result in results:
                    video_ids.append(result["_id"])
            if query_str:
                print('Video Size: ', video_ids)
                res_dict = self.global_search(query_str, video_ids,
                                              isBluE=isBluE)
                # print('res_dict: ',res_dict)
                for video_id in res_dict:
                    result = self.video_collection.find_one({"_id": video_id},
                                                            {"_id": 1,
                                                             "full_cn_str": 1})
                    full_cn_str = result['full_cn_str']
                    if res_dict[video_id]["type"] == "subtitle":
                        char_dur, time_dur = self.result_transformer(video_id,
                                                                     res_dict[
                                                                         video_id][
                                                                         'pos'])
                        match_frame[video_id] = {
                            "matched_str": res_dict[video_id]['matched_str'],
                            "start_time": time_dur[0],
                            "end_time": time_dur[1],
                            "subs_pos": char_dur,
                            "whole_str": full_cn_str[
                                         char_dur[0]:char_dur[1] + 1],
                            "video_id": video_id,
                            "type": "subtitle"}
                    else:
                        match_frame[video_id] = {
                            "matched_str": res_dict[video_id]['matched_str'],
                            "video_id": video_id,
                            "type": res_dict[video_id]["type"]
                        }
                    match_ids.append(video_id)
            else:
                match_ids.extend(video_ids)
            if match_ids:
                results = self.video_collection.find(
                    {"_id": {"$in": match_ids}, "state": 2})
                for result in results:
                    dict_search = {}
                    dict_search['video_id'] = result['_id']
                    dict_search['title'] = result['title']
                    dict_search['user_id'] = result['user_id']
                    dict_search['category'] = result['category']
                    # dict_search['video_path'] = {"720P":result['video_path']}
                    dict_search['title'] = result['title']
                    dict_search['lang'] = result['lang']
                    dict_search['description'] = result['description']
                    dict_search['upload_date'] = result['upload_time']
                    dict_search['image_path'] = result['image_path']
                    dict_search['video_view'] = "10"
                    dict_search['like_count'] = "500"
                    dict_search['comment_count'] = "100"
                    # dict_search['webvtt'] = result['webvtt']
                    if query_str:
                        dict_search['match_frame'] = match_frame[result['_id']]
                    result_data.append(dict_search)
        if mode == 'local':
            res_dict = self.local_search(query_str, video_ids[0],
                                         isSemantic=isSemantic)
            result = self.video_collection.find_one({"_id": video_ids[0]},
                                                    {"video_path": 1, "_id": 1,
                                                     "full_cn_str": 1})
            video_path = result['video_path']
            full_cn_str = result['full_cn_str']
            for _num in res_dict:
                video_id = res_dict[_num]['video_id']
                pos = res_dict[_num]['pos']
                char_dur, time_dur = self.result_transformer(video_id, pos)
                # time = time_format(float(time_dur[0]))
                # mobile = '15642336090'
                # output_directory = './static/picture/' + mobile + '_' + video_id
                # if not os.path.exists(output_directory):
                #     os.makedirs(output_directory)
                # output_path = output_directory + '/' + str(_num) + '.jpg'
                # image_path = generate_picture(video_path, output_path, time)
                match_frame = {
                    "matched_str": res_dict[_num]['matched_str'],
                    "start_time": time_dur[0],
                    "end_time": time_dur[1],
                    "subs_pos": char_dur,
                    "whole_str": full_cn_str[char_dur[0]:char_dur[1] + 1],
                    # "image_path": image_path,
                    "video_id": video_id}
                match_frames.append(match_frame)
            dict_search = {}
            dict_search['match_frame'] = match_frames
            result_data.append(dict_search)

        return result_data

    def global_search(self, query_str, video_ids, isBluE=False):

        inputs_dict = self.get_global_input_dict(video_ids)
        # print("inputs_dict:",inputs_dict)
        res_dict = {}

        if not isBluE:
            for video_id in inputs_dict:
                curr_str = inputs_dict[video_id]
                if query_str in curr_str:
                    matched_index = curr_str.index(query_str)
                    res_dict[video_id] = {
                        'pos': [matched_index,
                                matched_index + len(query_str) + 1],
                        'matched_str': query_str
                    }

        if isBluE:
            bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
                                              isSemantic=0, max_size=100)
            for item in bluE_results:
                curr_key = item['key_id']
                str_pos = item['str_position']
                if curr_key not in res_dict:
                    res_dict[curr_key] = {
                        'pos': str_pos,
                        'matched_str': item['matched_str'],
                        'type': "subtitle"
                    }
            des_dict = {}
            des_dict = res_dict.copy()
            # print('des_dict:',des_dict)
            for key in list(des_dict.keys()):
                if "description" in key:
                    # new_key = key.split('_')[1]
                    new_key = key[key.index('_') + 1:]
                    des_dict[new_key] = res_dict[key]
                    des_dict[new_key]["type"] = "description"
                    des_dict.pop(key)
            title_dict = {}
            title_dict = des_dict.copy()
            # print('title_dict:',title_dict)
            for key in list(title_dict.keys()):
                if "title" in key:
                    # new_key = key.split('_')[1]
                    new_key = key[key.index('_') + 1:]
                    title_dict[new_key] = des_dict[key]
                    title_dict[new_key]["type"] = "title"
                    title_dict.pop(key)
        return title_dict

    def get_input_dict(self, video_ids):

        res_dict = {}
        if video_ids:
            results = self.video_collection.find(
                {"_id": {"$in": video_ids}, "state": 2},
                {"full_cn_str": 1, "_id": 1})
        else:
            results = self.video_collection.find({"state": 2},
                                                 {"full_cn_str": 1, "_id": 1})
        for result in results:
            res_dict[result["_id"]] = result["full_cn_str"]
        return res_dict

    def get_global_input_dict(self, video_ids):

        res_dict = {}
        if video_ids:
            results = self.video_collection.find(
                {"_id": {"$in": video_ids}, "state": 2},
                {"full_cn_str": 1, "_id": 1, "title": 1, "description": 1})
        else:
            results = self.video_collection.find({"state": 2},
                                                 {"full_cn_str": 1, "_id": 1,
                                                  "title": 1, "description": 1})
        for result in results:
            key = result["_id"]
            res_dict[key] = result["full_cn_str"]
            if "title" in result and result["title"]:
                res_dict["title_" + key] = result["title"]
            if "description" in result and result["description"]:
                res_dict["description_" + key] = result["description"]
        return res_dict

    def bluE_standard(self, query_str, input_paragraph, lang='ch', isSemantic=0,
                      max_size=10):

        _url = 'http://codes.haetek.com:6675/blue'
        _data = {
            "dbmodelname": "blue",
            "modelaction": "search",
            "extradata": {
                "querystring": query_str,
                "paragraph": input_paragraph,
                "lang": lang,
                "issemantic": isSemantic,
                "isjson": True
            },
            "modeltype": "ai"
        }
        res = requests.post(url=_url, json=_data)
        res = json.loads(res.text)['resultdata']
        raw_res = res[1:max_size + 1]

        return raw_res

    def local_search(self, query_str, video_id, isSemantic=True):

        res_dict = {}
        curr_key = 0
        inputs_dict = self.get_input_dict([video_id])
        bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
                                          isSemantic=isSemantic, max_size=10)
        for item in bluE_results:
            video_id = item['key_id']
            str_pos = item['str_position']
            # toDo generating multiple results
            if curr_key < 5:
                res_dict[curr_key] = {
                    'video_id': video_id,
                    'pos': str_pos,
                    'matched_str': item['matched_str']
                }
                curr_key += 1

        return res_dict

    def result_transformer(self, video_id, res_pos):

        res_charId_bg = int(res_pos[0])
        res_charId_ed = int(res_pos[1])

        result = self.video_collection.find_one({"_id": video_id},
                                                {"char_id_to_time": 1})

        charId_to_time = result["char_id_to_time"]

        extrinsic_char_bg = 0
        extrinsic_char_ed = 0

        for raw_char_id in charId_to_time:
            char_id = int(raw_char_id)
            if char_id <= res_charId_bg:
                if char_id > extrinsic_char_bg or extrinsic_char_bg == 0:
                    extrinsic_char_bg = char_id

            if char_id >= res_charId_ed:
                if char_id < extrinsic_char_ed or extrinsic_char_ed == 0:
                    extrinsic_char_ed = char_id

        extrinsic_time_bg = charId_to_time[str(extrinsic_char_bg)]
        extrinsic_time_ed = charId_to_time[str(extrinsic_char_ed)]

        return [extrinsic_char_bg, extrinsic_char_ed], [extrinsic_time_bg,
                                                        extrinsic_time_ed]


def connect_mongodb():
    '''

    :return:
    '''
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
    client = MongoClient(host=mongodb_host, username=mongodb_user,
                         password=mongodb_password,
                         authSource=mongodb_db,
                         authMechanism=mongodb_authMechanism, port=mongodb_port)
    database = client.get_database(mongodb_db)
    return database


def main():
    print('Start')
    print()
    ###### Sample One (Local Search) ######

    video_ids = ['b47f7dd5c45c9839e2b6f56dcb300239']
    query_str = '超弦理论一共存在几种类型？'

    ss = time.time()
    s = Search()
    res_list = s.video_search(query_str, video_ids, mode='local')

    ee = time.time()

    print('###### Sample One (Local Search) ######')
    print('Query:', query_str)
    pprint.pprint(res_list)
    print('Video Size:', len(video_ids))
    print('Time Cost: ', ee - ss)
    print()

    ###### Sample Two (Global Search) ######

    # video_ids = ['unique_id1','unique_id2','unique_id5','unique_id7']
    # video_ids = []
    # query_str = '如何搭建神经网络'

    # ss = time.time()
    # s = Search()
    # res_list = s.video_search(query_str, video_ids, mode='global')

    # ee = time.time()

    # print('###### Sample Two (Global Search) ######')
    # print('Query:',query_str)
    # pprint.pprint(res_list)
    # print('Video Size:',len(video_ids))
    # print('Time Cost: ', ee-ss)


if __name__ == "__main__":
    main()


