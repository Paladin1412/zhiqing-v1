# import json
# import os
# import time
# import pprint
# import random
# import string
# import hashlib
# import urllib
# import requests
# import http.client
# from configparser import ConfigParser
# from pymongo import MongoClient, ReadPreference
#
# #
# class Search:
#     def __init__(self):
#         database = connect_mongodb()
#         self.video_collection = database.video
#         self.user_collection = database.user
#         self.like_collection = database.like
#         self.comment_collection = database.comment
#         self.subscription_collection = database.subscription
#         self.series_collection = database.series
#         self.tool_collection = database.tool
#
#     def get_series(self):
#         res_dict = {}
#         results = self.series_collection.find({}, {'title': 1, '_id': 1,
#                                                    'description': 1})
#         for result in results:
#             key = result["_id"]
#             res_dict[key] = result["title"]
#         return res_dict
#
#     def series_search(self, query_str):
#         inputs_dict = self.get_series()
#         res_dict = {}
#         bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
#                                           isSemantic=0, max_size=100)
#         for item in bluE_results:
#             curr_key = item['key_id']
#             str_pos = item['str_position']
#             if curr_key not in res_dict:
#                 res_dict[curr_key] = {
#                     'pos': str_pos,
#                     'matched_str': item['matched_str'],
#                     'type': "title",
#                     'score': item['match_score']
#                 }
#         return res_dict
#
#     def get_users(self):
#         res_dict = {}
#         results = self.user_collection.find({}, {'name': 1, '_id': 1})
#         for result in results:
#             res_dict[result['_id']] = result['name']
#         return res_dict
#
#     def user_search(self, query_str):
#         inputs_dict = self.get_users()
#         bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
#                                           isSemantic=0, max_size=100)
#         res_dict = {}
#         for item in bluE_results:
#             curr_key = item['key_id']
#             str_pos = item['str_position']
#             if curr_key not in res_dict:
#                 res_dict[curr_key] = {
#                     'pos': str_pos,
#                     'matched_str': item['matched_str'],
#                     'score': item['match_score']
#                 }
#         return res_dict
#
#     def local_search(self, query_str, video_ids, isBluE=True, isSemantic=True):
#         result_data = []
#         match_frame = {}
#         match_frames = []
#         tool = self.tool_collection.find_one({'type': 'category'})
#         res_dict = self.local_video_search(query_str, video_ids[0],
#                                            isSemantic=isSemantic)
#         result = self.video_collection.find_one({"_id": video_ids[0]},
#                                                 {"video_path": 1, "_id": 1,
#                                                  "full_cn_str": 1})
#         video_path = result['video_path']
#         full_cn_str = result['full_cn_str']
#         for _num in res_dict:
#             video_id = res_dict[_num]['video_id']
#             pos = res_dict[_num]['pos']
#             char_dur, time_dur = self.result_transformer(video_id, pos)
#
#             match_frame = {
#                 "matched_str": res_dict[_num]['matched_str'],
#                 "start_time": time_dur[0],
#                 "end_time": time_dur[1],
#                 "subs_pos": char_dur,
#                 "whole_str": full_cn_str[char_dur[0]:char_dur[1] + 1],
#                 "video_id": video_id}
#             match_frames.append(match_frame)
#         dict_search = {}
#         dict_search['match_frame'] = match_frames
#         result_data.append(dict_search)
#
#         return result_data
#
#     def global_search(self, query_str, video_ids, type, max_size, page,
#                       isBluE=True, isSemantic=True):
#
#         result_data = []
#         temp_data = []
#         compare = {}
#         match_frame = {}
#         match_frames = []
#         match_ids = []
#         tool = self.tool_collection.find_one({'type': 'category'})
#         if not video_ids:
#             results = self.video_collection.find({"state": 2}, {"_id": 1})
#             for result in results:
#                 video_ids.append(result["_id"])
#         video_num = 0
#         series_num = 0
#         user_num = 0
#         if type in ['video', 'all']:
#             print('Video Size: ', video_ids)
#             res_dict = self.video_search(query_str, video_ids, isBluE=isBluE)
#             print('res_dict: ', res_dict)
#             for video_id in res_dict:
#                 result = self.video_collection.find_one({"_id": video_id},
#                                                         {"_id": 1,
#                                                          "full_cn_str": 1})
#                 full_cn_str = result['full_cn_str']
#                 if res_dict[video_id]["type"] == "subtitle":
#                     char_dur, time_dur = self.result_transformer(video_id,
#                                                                  res_dict[
#                                                                      video_id][
#                                                                      'pos'])
#                     match_frame[video_id] = {
#                         "matched_str": res_dict[video_id]['matched_str'],
#                         "score": res_dict[video_id]['score'],
#                         "start_time": time_dur[0],
#                         "end_time": time_dur[1],
#                         "subs_pos": char_dur,
#                         "whole_str": full_cn_str[char_dur[0]:char_dur[1] + 1],
#                         "type": "subtitle"}
#                 else:
#                     match_frame[video_id] = {
#                         "matched_str": res_dict[video_id]['matched_str'],
#                         "type": res_dict[video_id]["type"],
#                         "score": res_dict[video_id]['score']
#                     }
#                 match_ids.append(video_id)
#
#             if match_ids:
#                 results = self.video_collection.find(
#                     {"_id": {"$in": match_ids}, "state": 2})
#                 for result in results:
#                     category = []
#                     for category_number in result['category']:
#                         category.append(tool['data'][category_number])
#                     video_num += 1
#                     user_id = result['user_id']
#                     video_id = result['_id']
#                     user = self.user_collection.find_one({"_id": user_id},
#                                                          {"name": 1, "_id": 1,
#                                                           "headshot": 1})
#                     like_counts = self.like_collection.find(
#                         {"relation_id": video_id, "type": "video"}).count()
#                     comment_counts = self.comment_collection.find(
#                         {"video_id": video_id}).count()
#                     dict_search = {}
#                     dict_search['source'] = 'video'
#                     data = dict_search['data'] = {}
#                     data['video_id'] = video_id
#                     data['title'] = result['title']
#                     data['user_id'] = user_id
#                     data['user_name'] = user['name']
#                     data['headshot'] = user['headshot']
#                     data['category'] = category
#                     data['lang'] = result['lang']
#                     data['description'] = result['description']
#                     data['upload_time'] = result['upload_time']
#                     data['image_path'] = result['image_path']
#                     data['view_counts'] = result.get("view_counts", None) if result.get("view_counts", None) else 0
#                     data['like_counts'] = like_counts
#                     data['comment_counts'] = comment_counts
#                     dict_search['match_frame'] = match_frame[result['_id']]
#                     if video_num < 4:
#                         result_data.append(dict_search)
#                     else:
#                         temp_data.append(dict_search)
#                         compare[str(video_num - 4)] = \
#                         match_frame[result['_id']]['score']
#
#         if type in ['user', 'all']:
#             user_dict = self.user_search(query_str)
#             for user_id in user_dict:
#                 if user_id:
#                     user_num += 1
#                     user = self.user_collection.find_one({'_id': user_id})
#                     video_counts = self.video_collection.find(
#                         {"user_id": user_id}).count()
#                     subscription_counts = self.subscription_collection.find(
#                         {"user_id": user_id}).count()
#                     dict_search = {}
#                     dict_search['source'] = 'user'
#                     data = dict_search['data'] = {}
#                     data['user_id'] = user_id
#                     data['headshot'] = user['headshot']
#                     data['user_name'] = user['name']
#                     data['introduction'] = user['introduction']
#                     data['video_counts'] = video_counts
#                     data['subscription_counts'] = subscription_counts
#                     dict_search['match_frame'] = {
#                         'matched_str': user_dict[user_id]['matched_str'],
#                         'score': user_dict[user_id]['score']}
#                     if user_num < 4:
#                         result_data.append(dict_search)
#                     else:
#                         temp_data.append(dict_search)
#                         compare[str(video_num + user_num - 4)] = \
#                         match_frame[result['_id']]['score']
#
#         if type in ['series', 'all']:
#             series_dict = self.series_search(query_str)
#             for series_id in series_dict:
#                 if series_id:
#                     series_num += 1
#                     series = self.series_collection.find_one({'_id': series_id})
#                     category = []
#                     for category_number in series['category']:
#                         category.append(tool['data'][category_number])
#                     view_counts = 0
#                     video_ids = []
#                     results = self.video_collection.find(
#                         {'series_id': series_id})
#                     for result in results:
#                         video_ids.append(result['_id'])
#                         view_counts += result['view_counts']
#                     user = self.user_collection.find_one(
#                         {"_id": series['user_id']},
#                         {"name": 1, "_id": 1, "headshot": 1})
#                     like_counts = self.like_collection.find(
#                         {"relation_id": {'$in': video_id},
#                          "type": "video"}).count()
#                     comment_counts = self.comment_collection.find(
#                         {"video_id": {'$in': video_id}}).count()
#                     dict_search = {}
#                     dict_search['source'] = 'series'
#                     data = dict_search['data'] = {}
#                     data['series_id'] = series_id
#                     data['user_id'] = series['user_id']
#                     data['user_name'] = user['name']
#                     data['headshot'] = user['headshot']
#                     data['title'] = series['title']
#                     data['category'] = category
#                     data['description'] = series['description']
#                     data['image_path'] = series['image_path']
#                     data['upload_time'] = series['time']
#                     data['view_counts'] = view_counts
#                     data['like_counts'] = like_counts
#                     data['comment_counts'] = comment_counts
#                     dict_search['match_frame'] = {
#                         'matched_str': series_dict[series_id]['matched_str'],
#                         'type': series_dict[series_id]['type'],
#                         'score': series_dict[series_id]['score']}
#                     if user_num < 4:
#                         result_data.append(dict_search)
#                     else:
#                         temp_data.append(dict_search)
#                         compare[str(series_num + video_num + user_num - 4)] = \
#                         match_frame[result['_id']]['score']
#         compare_list = sorted(compare.items(), key=lambda x: x[1], reverse=True)
#         for num in compare_list[max_size * (page - 1):max_size * page]:
#             # result_data.append(temp_data[num])
#             result_data.append(temp_data[int(num[0])])
#         return result_data
#
#     def video_search(self, query_str, video_ids, isBluE=False):
#
#         inputs_dict = self.get_video(video_ids)
#         res_dict = {}
#
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
#                 # print(item)
#                 curr_key = item['key_id']
#                 str_pos = item['str_position']
#                 if curr_key not in res_dict:
#                     res_dict[curr_key] = {
#                         'pos': str_pos,
#                         'matched_str': item['matched_str'],
#                         'type': "subtitle",
#                         'score': item['match_score']
#                     }
#             title_dict = {}
#             title_dict = res_dict.copy()
#             # print('title_dict:',title_dict)
#             for key in list(title_dict.keys()):
#                 if "title" in key:
#                     # new_key = key.split('_')[1]
#                     new_key = key[key.index('_') + 1:]
#                     title_dict[new_key] = res_dict[key]
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
#     def get_video(self, video_ids):
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
#     def local_video_search(self, query_str, video_id, isSemantic=True):
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
#             if curr_key < 5:
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
#     database = client.get_database(mongodb_db)
#     return database
#
#
# def main():
#     print('Start')
#     print()
#     ###### Sample One (Local Search) ######
#
#     # video_ids = ['4339af28471e62289847391fab65b149']
#     # query_str = '向量'
#
#     # ss = time.time()
#     # s = Search()
#     # res_list = s.local_search(query_str, video_ids)
#
#     # ee = time.time()
#
#     # print('###### Sample One (Local Search) ######')
#     # print('Query:',query_str)
#     # pprint.pprint(res_list)
#     # print('Video Size:',len(video_ids))
#     # print('Time Cost: ', ee-ss)
#     # print()
#
#     ###### Sample Two (Global Search) ######
#
#     video_ids = []
#     # query_str = '向量'
#     query_str = 'python'
#
#     ss = time.time()
#     s = Search()
#     type = 'all'
#     max_size = 10
#     page = 1
#     res_list = s.global_search(query_str, video_ids, type, max_size, page)
#
#     ee = time.time()
#
#     print('###### Sample Two (Global Search) ######')
#     print('Query:', query_str)
#     pprint.pprint(res_list)
#     print('Video Size:', len(video_ids))
#     print('Time Cost: ', ee - ss)
#
#
# if __name__ == "__main__":
#     main()
#
#


# -*- coding: utf-8 -*-
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
#         self.user_collection = database.user
#         self.like_collection = database.like
#         self.comment_collection = database.comment
#         self.subscription_collection = database.subscription
#         self.series_collection = database.series
#         self.tool_collection = database.tool
#
#     def get_series(self):
#         res_dict = {}
#         results = self.series_collection.find({}, {'title': 1, '_id': 1,
#                                                    'description': 1})
#         for result in results:
#             key = result["_id"]
#             res_dict[key] = result["title"]
#         return res_dict
#
#     def series_search(self, query_str):
#         inputs_dict = self.get_series()
#         res_dict = {}
#         bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
#                                           isSemantic=0, max_size=100)
#         for item in bluE_results:
#             curr_key = item['key_id']
#             str_pos = item['str_position']
#             if curr_key not in res_dict:
#                 res_dict[curr_key] = {
#                     'pos': str_pos,
#                     'matched_str': item['matched_str'],
#                     'type': "title",
#                     'score': item['match_score']
#                 }
#         return res_dict
#
#     def get_users(self):
#         res_dict = {}
#         results = self.user_collection.find({}, {'name': 1, '_id': 1})
#         for result in results:
#             res_dict[result['_id']] = result['name']
#         return res_dict
#
#     def user_search(self, query_str):
#         inputs_dict = self.get_users()
#         bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
#                                           isSemantic=0, max_size=100)
#         res_dict = {}
#         for item in bluE_results:
#             curr_key = item['key_id']
#             str_pos = item['str_position']
#             if curr_key not in res_dict:
#                 res_dict[curr_key] = {
#                     'pos': str_pos,
#                     'matched_str': item['matched_str'],
#                     'score': item['match_score']
#                 }
#         return res_dict
#
#     def local_search(self, query_str, video_ids, isBluE=True, isSemantic=True):
#         result_data = []
#         match_frame = {}
#         match_frames = []
#         tool = self.tool_collection.find_one({'type': 'category'})
#         res_dict = self.local_video_search(query_str, video_ids[0],
#                                            isSemantic=isSemantic)
#         result = self.video_collection.find_one({"_id": video_ids[0]},
#                                                 {"video_path": 1, "_id": 1,
#                                                  "full_cn_str": 1})
#         video_path = result['video_path']
#         full_cn_str = result['full_cn_str']
#         for _num in res_dict:
#             video_id = res_dict[_num]['video_id']
#             pos = res_dict[_num]['pos']
#             char_dur, time_dur = self.result_transformer(video_id, pos)
#
#             match_frame = {
#                 "matched_str": res_dict[_num]['matched_str'],
#                 "start_time": time_dur[0],
#                 "end_time": time_dur[1],
#                 "subs_pos": char_dur,
#                 "whole_str": full_cn_str[char_dur[0]:char_dur[1] + 1],
#                 "video_id": video_id}
#             match_frames.append(match_frame)
#         dict_search = {}
#         dict_search['match_frame'] = match_frames
#         result_data.append(dict_search)
#
#         return result_data
#
#     def global_search(self, query_str, video_ids, type, max_size, page,
#                       isBluE=True, isSemantic=True):
#
#         result_data = []
#         temp_data = []
#         compare = {}
#         match_frame = {}
#         match_frames = []
#         match_ids = []
#         tool = self.tool_collection.find_one({'type': 'category'})
#         if not video_ids:
#             results = self.video_collection.find({"state": 2}, {"_id": 1})
#             for result in results:
#                 video_ids.append(result["_id"])
#         video_num = 0
#         series_num = 0
#         user_num = 0
#         if type in ['video', 'all']:
#             # print('Video Size: ',video_ids)
#             res_dict = self.video_search(query_str, video_ids, isBluE=isBluE)
#             # print('res_dict: ',res_dict)
#             for video_id in res_dict:
#                 if video_id:
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
#                             "score": res_dict[video_id]['score'],
#                             "start_time": time_dur[0],
#                             "end_time": time_dur[1],
#                             "subs_pos": char_dur,
#                             "whole_str": full_cn_str[
#                                          char_dur[0]:char_dur[1] + 1],
#                             "type": "subtitle"}
#                     else:
#                         match_frame[video_id] = {
#                             "matched_str": res_dict[video_id]['matched_str'],
#                             "type": res_dict[video_id]["type"],
#                             "score": res_dict[video_id]['score']
#                         }
#                     match_ids.append(video_id)
#
#             if match_ids:
#                 results = self.video_collection.find(
#                     {"_id": {"$in": match_ids}, "state": 2})
#                 for result in results:
#                     category = []
#                     for category_number in result['category']:
#                         category.append(tool['data'][category_number])
#                     video_num += 1
#                     user_id = result['user_id']
#                     video_id = result['_id']
#                     user = self.user_collection.find_one({"_id": user_id},
#                                                          {"name": 1, "_id": 1,
#                                                           "headshot": 1})
#                     like_counts = self.like_collection.find(
#                         {"relation_id": video_id, "type": "video"}).count()
#                     comment_counts = self.comment_collection.find(
#                         {"video_id": video_id}).count()
#                     dict_search = {}
#                     dict_search['source'] = 'video'
#                     data = dict_search['data'] = {}
#                     data['video_id'] = video_id
#                     data['title'] = result['title']
#                     data['user_id'] = user_id
#                     data['user_name'] = user['name']
#                     data['headshot'] = user['headshot']
#                     data['category'] = category
#                     data['lang'] = result['lang']
#                     data['description'] = result['description']
#                     data['upload_time'] = result['upload_time']
#                     data['image_path'] = result['image_path']
#                     data['view_counts'] = result.get("view_counts", None) if result.get("view_counts", None) else 0
#                     data['like_counts'] = like_counts
#                     data['comment_counts'] = comment_counts
#                     dict_search['match_frame'] = match_frame[result['_id']]
#                     if video_num < 4:
#                         result_data.append(dict_search)
#                     else:
#                         temp_data.append(dict_search)
#                         compare[str(video_num - 4)] = \
#                         match_frame[result['_id']]['score']
#
#         if type in ['user', 'all']:
#             user_dict = self.user_search(query_str)
#             for user_id in user_dict:
#                 if user_id:
#                     user_num += 1
#                     user = self.user_collection.find_one({'_id': user_id})
#                     video_counts = self.video_collection.find(
#                         {"user_id": user_id}).count()
#                     subscription_counts = self.subscription_collection.find(
#                         {"user_id": user_id}).count()
#                     dict_search = {}
#                     dict_search['source'] = 'user'
#                     data = dict_search['data'] = {}
#                     data['user_id'] = user_id
#                     data['headshot'] = user['headshot']
#                     data['user_name'] = user['name']
#                     data['introduction'] = user['introduction']
#                     data['video_counts'] = video_counts
#                     data['subscription_counts'] = subscription_counts
#                     dict_search['match_frame'] = {
#                         'matched_str': user_dict[user_id]['matched_str'],
#                         'score': user_dict[user_id]['score']}
#                     if user_num < 4:
#                         result_data.append(dict_search)
#                     else:
#                         temp_data.append(dict_search)
#                         compare[str(video_num + user_num - 4)] = \
#                         match_frame[result['_id']]['score']
#
#         if type in ['series', 'all']:
#             series_dict = self.series_search(query_str)
#             for series_id in series_dict:
#                 if series_id:
#                     series_num += 1
#                     series = self.series_collection.find_one({'_id': series_id})
#                     category = []
#                     for category_number in series['category']:
#                         category.append(tool['data'][category_number])
#                     view_counts = 0
#                     video_ids = []
#                     results = self.video_collection.find(
#                         {'series_id': series_id})
#                     for result in results:
#                         video_ids.append(result['_id'])
#                         view_counts += result['view_counts']
#                     user = self.user_collection.find_one(
#                         {"_id": series['user_id']},
#                         {"name": 1, "_id": 1, "headshot": 1})
#                     like_counts = self.like_collection.find(
#                         {"relation_id": {'$in': video_id},
#                          "type": "video"}).count()
#                     comment_counts = self.comment_collection.find(
#                         {"video_id": {'$in': video_id}}).count()
#                     dict_search = {}
#                     dict_search['source'] = 'series'
#                     data = dict_search['data'] = {}
#                     data['series_id'] = series_id
#                     data['user_id'] = series['user_id']
#                     data['user_name'] = user['name']
#                     data['headshot'] = user['headshot']
#                     data['title'] = series['title']
#                     data['category'] = category
#                     data['description'] = series['description']
#                     data['image_path'] = series['image_path']
#                     data['upload_time'] = series['time']
#                     data['view_counts'] = view_counts
#                     data['like_counts'] = like_counts
#                     data['comment_counts'] = comment_counts
#                     dict_search['match_frame'] = {
#                         'matched_str': series_dict[series_id]['matched_str'],
#                         'type': series_dict[series_id]['type'],
#                         'score': series_dict[series_id]['score']}
#                     if user_num < 4:
#                         result_data.append(dict_search)
#                     else:
#                         temp_data.append(dict_search)
#                         compare[str(series_num + video_num + user_num - 4)] = \
#                         match_frame[result['_id']]['score']
#         compare_list = sorted(compare.items(), key=lambda x: x[1], reverse=True)
#         for num in compare_list[max_size * (page - 1):max_size * page]:
#             # result_data.append(temp_data[num])
#             result_data.append(temp_data[int(num[0])])
#         return result_data
#
#     def video_search(self, query_str, video_ids, isBluE=False):
#
#         inputs_dict = self.get_video(video_ids)
#         res_dict = {}
#
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
#                 # print(item)
#                 curr_key = item['key_id']
#                 str_pos = item['str_position']
#                 if curr_key not in res_dict:
#                     res_dict[curr_key] = {
#                         'pos': str_pos,
#                         'matched_str': item['matched_str'],
#                         'type': "subtitle",
#                         'score': item['match_score']
#                     }
#             title_dict = {}
#             title_dict = res_dict.copy()
#             print('title_dict:', title_dict)
#             for key in list(title_dict.keys()):
#                 if "title" in key:
#                     # new_key = key.split('_')[1]
#                     new_key = key[key.index('_') + 1:]
#                     title_dict[new_key] = res_dict[key]
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
#     def get_video(self, video_ids):
#
#         res_dict = {}
#         if video_ids:
#             results = self.video_collection.find(
#                 {"_id": {"$in": video_ids}, "state": 2},
#                 {"full_cn_str": 1, "_id": 1, "title": 1})
#         else:
#             results = self.video_collection.find({"state": 2},
#                                                  {"full_cn_str": 1, "_id": 1,
#                                                   "title": 1})
#         for result in results:
#             key = result["_id"]
#             res_dict[key] = result["full_cn_str"]
#             if "title" in result and result["title"]:
#                 res_dict["title_" + key] = result["title"]
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
#     def local_video_search(self, query_str, video_id, isSemantic=True):
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
#             if curr_key < 5:
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
#     database = client.get_database(mongodb_db)
#     return database
#
#
# def main():
#     print('Start')
#     print()
#     ###### Sample One (Local Search) ######
#
#     # video_ids = ['162fb70b08169805aab916f75711b015']
#     # query_str = '宇宙的维度是'
#     #
#     # ss = time.time()
#     # s = Search()
#     # res_list = s.local_search(query_str, video_ids)
#     #
#     # ee = time.time()
#     #
#     # print('###### Sample One (Local Search) ######')
#     # print('Query:',query_str)
#     # pprint.pprint(res_list)
#     # print('Video Size:',len(video_ids))
#     # print('Time Cost: ', ee-ss)
#     # print()
#
#     ###### Sample Two (Global Search) ######
#
#     video_ids = []
#     query_str = '向量'
#
#     ss = time.time()
#     s = Search()
#     type = 'all'
#     max_size = 10
#     page = 1
#     res_list = s.global_search(query_str, video_ids, type, max_size, page)
#
#     ee = time.time()
#
#     print('###### Sample Two (Global Search) ######')
#     print('Query:', query_str)
#     pprint.pprint(res_list)
#     print('Video Size:', len(video_ids))
#     print('Time Cost: ', ee - ss)
#
#
# if __name__ == "__main__":
#     main()
#
#


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
import packages.iflytek_api as voice_api
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
                'char_id_to_page_id': char_id_to_page_id
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
