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
#     query_str = '黑马'
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


# -*- coding: utf-8 -*-
#


import json
import os
import pprint
import time
from configparser import ConfigParser

import requests
from pymongo import MongoClient


def bluE_standard(query_str, input_paragraph, lang='ch', isSemantic=0,
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


class Search:
    def __init__(self):
        self.database = connect_mongodb()

    def get_document(self):
        """

        :return:
        """
        res_dict = {}
        map_dict = {}
        documents = self.database.document.find({}, {'full_str': 1, '_id': 1,
                                                     'char_id_to_page_id': 1})
        for document in documents:
            key = document["_id"]
            res_dict[key] = document["full_str"]
            map_dict[key] = document["char_id_to_page_id"]
        return res_dict, map_dict

    def document_search(self, query_str):
        """

        :param query_str:
        :return:
        """
        res_list = []
        added_ids = []
        added_pages = []

        input_paragraph, map_dict = self.get_document()
        bluE_results = bluE_standard(query_str, input_paragraph, lang='ch',
                                     isSemantic=0, max_size=100)
        for res_item in bluE_results:
            matched_id = res_item['key_id']
            matched_str = res_item['matched_str']
            matched_pos = res_item['str_position']
            score = res_item['match_score']
            matched_page = 0
            matched_str_enlarge = input_paragraph[matched_id][
                                  max(int(matched_pos[0]) - 10, 0):min(
                                      int(matched_pos[1]) + 10
                                      , len(input_paragraph
                                            [matched_id]))]
            curr_map = map_dict[matched_id]
            for charId, pageId in curr_map:
                if int(matched_pos[0]) <= int(charId):
                    matched_page = int(pageId) - 1
                    break

            if added_ids.count(matched_id) < 3 and [matched_id,
                                                    matched_page] not in added_pages:
                res_list.append({
                    'matched_id': matched_id,
                    'matched_pos': matched_pos,
                    'matched_str': matched_str,
                    'matched_page': matched_page,
                    'matched_str_enlarge': matched_str_enlarge,
                    'score': score
                })
                added_ids.append(matched_id)
                added_pages.append([matched_id, matched_page])
        return res_list

    def get_series(self):
        """

        :return:
        """
        res_dict = {}
        results = self.database.series.find({}, {'title': 1, '_id': 1})
        for series in results:
            key = series["_id"]
            res_dict[key] = series["title"]
        return res_dict

    def series_search(self, query_str):
        """

        :param query_str:
        :return:
        """
        inputs_dict = self.get_series()
        res_dict = {}
        bluE_results = bluE_standard(query_str, inputs_dict, lang='ch',
                                     isSemantic=0, max_size=100)
        for item in bluE_results:
            curr_key = item['key_id']
            str_pos = item['str_position']
            if curr_key not in res_dict:
                res_dict[curr_key] = {
                    'pos': str_pos,
                    'matched_str': item['matched_str'],
                    'type': "title",
                    'score': item['match_score']
                }
        return res_dict

    def get_users(self):
        """

        :return res_dict:
        """
        res_dict = {}
        users = self.database.user.find({}, {'name': 1, '_id': 1})
        for user in users:
            res_dict[user['_id']] = user['name']
        return res_dict

    def user_search(self, query_str):
        """

        :param query_str:
        :return res_dict:
        """
        inputs_dict = self.get_users()
        bluE_results = bluE_standard(query_str, inputs_dict, lang='ch',
                                     isSemantic=0, max_size=100)
        res_dict = {}
        for item in bluE_results:
            curr_key = item['key_id']
            str_pos = item['str_position']
            if curr_key not in res_dict:
                res_dict[curr_key] = {
                    'pos': str_pos,
                    'matched_str': item['matched_str'],
                    'score': item['match_score']
                }
        return res_dict

    def local_search(self, query_str, video_ids, isSemantic=True):
        """
        局部搜索
        :param query_str:
        :param video_ids:
        :param isSemantic:
        :return result_data:
        """
        result_data = []
        match_frames = []
        res_dict = self.local_video_search(query_str, video_ids[0],
                                           isSemantic=isSemantic)
        result = self.database.video.find_one({"_id": video_ids[0]},
                                              {"video_path": 1, "_id": 1,
                                               "full_cn_str": 1})
        full_cn_str = result['full_cn_str']
        for _num in res_dict:
            video_id = res_dict[_num]['video_id']
            pos = res_dict[_num]['pos']
            char_dur, time_dur = self.result_transformer(video_id, pos)

            match_frame = {
                "matched_str": res_dict[_num]['matched_str'],
                "start_time": time_dur[0],
                "end_time": time_dur[1],
                "subs_pos": char_dur,
                "whole_str": full_cn_str[char_dur[0]:char_dur[1] + 1],
                "video_id": video_id}
            match_frames.append(match_frame)
        dict_search = {'match_frame': match_frames}
        result_data.append(dict_search)

        return result_data

    def global_search(self, query_str, video_ids, search_range, max_size, page,
                      isBluE=True):
        """
        全局搜索
        :param query_str:
        :param video_ids:
        :param search_range:
        :param max_size:
        :param page:
        :param isBluE:
        :return result_data:
        """
        result_data = []
        temp_data = []
        compare = {}
        match_frame = {}
        match_ids = []
        tool = self.database.tool.find_one({'type': 'category'})
        if not video_ids:
            videos = self.database.video.find({"state": 2}, {"_id": 1})
            for video in videos:
                video_ids.append(video["_id"])
        video_num = 0
        series_num = 0
        user_num = 0
        document_num = 0
        if search_range in ['video', 'all']:
            # print('Video Size: ',video_ids)
            res_dict = self.video_search(query_str, video_ids, isBluE=isBluE)
            # print('res_dict: ',res_dict)
            for video_id in res_dict:
                if video_id:
                    result = self.database.video.find_one({"_id": video_id},
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
                            "score": res_dict[video_id]['score'],
                            "start_time": time_dur[0],
                            "end_time": time_dur[1],
                            "subs_pos": char_dur,
                            "whole_str": full_cn_str[
                                         char_dur[0]:char_dur[1] + 1],
                            "type": "subtitle"}
                    else:
                        match_frame[video_id] = {
                            "matched_str": res_dict[video_id]['matched_str'],
                            "type": res_dict[video_id]["type"],
                            "score": res_dict[video_id]['score']
                        }
                    match_ids.append(video_id)

            if match_ids:
                results = self.database.video.find(
                    {"_id": {"$in": match_ids}, "state": 2})
                for result in results:
                    category = []
                    for category_number in result['category']:
                        category.append(tool['data'][category_number])
                    video_num += 1
                    user_id = result['user_id']
                    video_id = result['_id']
                    user = self.database.user.find_one({"_id": user_id},
                                                       {"name": 1, "_id": 1,
                                                        "headshot": 1})
                    like_counts = self.database.like.find(
                        {"relation_id": video_id, "type": "video"}).count()
                    comment_counts = self.database.comment.find(
                        {"video_id": video_id}).count()
                    dict_search = {'source': 'video'}
                    data = dict_search['data'] = {}
                    data['video_id'] = video_id
                    data['title'] = result['title']
                    data['user_id'] = user_id
                    data['user_name'] = user['name']
                    data['headshot'] = user['headshot']
                    data['category'] = category
                    data['lang'] = result['lang']
                    data['description'] = result['description']
                    data['upload_time'] = result['upload_time']
                    data['image_path'] = result['image_path']
                    data['view_counts'] = result['view_counts']
                    data['like_counts'] = like_counts
                    data['comment_counts'] = comment_counts
                    dict_search['match_frame'] = match_frame[video_id]
                    if video_num < 4:
                        result_data.append(dict_search)
                    else:
                        temp_data.append(dict_search)
                        compare[str(video_num - 4)] = match_frame[video_id][
                            'score']

        if search_range in ['user', 'all']:
            user_dict = self.user_search(query_str)
            for user_id in user_dict:
                if user_id:
                    user_num += 1
                    user = self.database.user.find_one({'_id': user_id})
                    video_counts = self.database.video.find(
                        {"user_id": user_id}).count()
                    subscription_counts = self.database.subscription.find(
                        {"user_id": user_id}).count()
                    dict_search = {'source': 'user'}
                    data = dict_search['data'] = {}
                    data['user_id'] = user_id
                    data['headshot'] = user['headshot']
                    data['user_name'] = user['name']
                    data['introduction'] = user['introduction']
                    data['video_counts'] = video_counts
                    data['subscription_counts'] = subscription_counts
                    dict_search['match_frame'] = {
                        'matched_str': user_dict[user_id]['matched_str'],
                        'score': user_dict[user_id]['score']}
                    if user_num < 4:
                        result_data.append(dict_search)
                    else:
                        temp_data.append(dict_search)
                        compare[str(video_num + user_num - 4)] = \
                            user_dict[user_id]['score']

        if search_range in ['series', 'all']:
            series_dict = self.series_search(query_str)
            for series_id in series_dict:
                if series_id:
                    series_num += 1
                    series = self.database.series.find_one({'_id': series_id})
                    category = []
                    for category_number in series['category']:
                        category.append(tool['data'][category_number])
                    view_counts = 0
                    video_ids = []
                    results = self.database.video.find({'series_id': series_id})
                    for result in results:
                        video_ids.append(result['_id'])
                        view_counts += result['view_counts']
                    user = self.database.user.find_one(
                        {"_id": series['user_id']},
                        {"name": 1, "_id": 1, "headshot": 1})
                    like_counts = self.database.like.find(
                        {"relation_id": {'$in': video_ids},
                         "type": "video"}).count()
                    comment_counts = self.database.command().find(
                        {"video_id": {'$in': video_ids}}).count()
                    dict_search = {'source': 'series'}
                    data = dict_search['data'] = {}
                    data['series_id'] = series_id
                    data['user_id'] = series['user_id']
                    data['user_name'] = user['name']
                    data['headshot'] = user['headshot']
                    data['title'] = series['title']
                    data['category'] = category
                    data['description'] = series['description']
                    data['image_path'] = series['image_path']
                    data['upload_time'] = series['time']
                    data['view_counts'] = view_counts
                    data['like_counts'] = like_counts
                    data['comment_counts'] = comment_counts
                    dict_search['match_frame'] = {
                        'matched_str': series_dict[series_id]['matched_str'],
                        'type': series_dict[series_id]['type'],
                        'score': series_dict[series_id]['score']}
                    if series_num < 4:
                        result_data.append(dict_search)
                    else:
                        temp_data.append(dict_search)
                        compare[str(series_num + video_num + user_num - 4)] = \
                            series_dict[series_id]['score']
        if search_range in ['document', 'all']:
            document_list = self.document_search(query_str)
            if document_list:
                for document_dict in document_list:
                    document_num += 1
                    dict_search = {'source': 'document'}
                    data = dict_search['data'] = {}
                    document_id = document_dict['matched_id']
                    document = self.database.document.find_one(
                        {'_id': document_id}, {'file_name': 1, 'type': 1})
                    data['document_id'] = document_id
                    data['file_name'] = document['file_name']
                    dict_search['match_frame'] = {
                        'matched_str': document_dict['matched_str'],
                        'matched_page': document_dict['matched_page'],
                        'matched_str_enlarge': document_dict[
                            'matched_str_enlarge'],
                        'score': document_dict['score']}
                    if series_num < 4:
                        result_data.append(dict_search)
                    else:
                        temp_data.append(dict_search)
                        compare[str(
                            document_num + series_num + video_num + user_num - 4)] = \
                            document_dict['score']

        compare_list = sorted(compare.items(), key=lambda x: x[1], reverse=True)
        for num in compare_list[max_size * (page - 1):max_size * page]:
            # result_data.append(temp_data[num])
            result_data.append(temp_data[int(num[0])])
        return result_data

    def video_search(self, query_str, video_ids, isBluE=False):
        """
        在视频数据中全局搜索
        :param query_str:
        :param video_ids:
        :param isBluE:
        :return title_dict:
        """
        inputs_dict = self.get_video(video_ids)
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
            bluE_results = bluE_standard(query_str, inputs_dict, lang='ch',
                                         isSemantic=0,
                                         max_size=100)
            for item in bluE_results:
                # print(item)
                curr_key = item['key_id']
                str_pos = item['str_position']
                if curr_key not in res_dict:
                    res_dict[curr_key] = {
                        'pos': str_pos,
                        'matched_str': item['matched_str'],
                        'type': "subtitle",
                        'score': item['match_score']
                    }
            title_dict = res_dict.copy()
            print('title_dict:', title_dict)
            for key in list(title_dict.keys()):
                if "title" in key:
                    # new_key = key.split('_')[1]
                    new_key = key[key.index('_') + 1:]
                    title_dict[new_key] = res_dict[key]
                    title_dict[new_key]["type"] = "title"
                    title_dict.pop(key)
        return title_dict

    def get_input_dict(self, video_ids):
        """
        获取局部搜索视频数据集合
        :param video_ids:
        :return:
        """
        res_dict = {}
        if video_ids:
            results = self.database.video.find(
                {"_id": {"$in": video_ids}, "state": 2},
                {"full_cn_str": 1, "_id": 1})
        else:
            results = self.database.video.find({"state": 2},
                                               {"full_cn_str": 1, "_id": 1})
        for result in results:
            res_dict[result["_id"]] = result["full_cn_str"]
        return res_dict

    def get_video(self, video_ids):
        """
        获取全局搜索视频数据集合
        :param video_ids:
        :return res_dict:
        """
        res_dict = {}
        if video_ids:
            results = self.database.video.find(
                {"_id": {"$in": video_ids}, "state": 2},
                {"full_cn_str": 1, "_id": 1, "title": 1})
        else:
            results = self.database.video.find({"state": 2},
                                               {"full_cn_str": 1, "_id": 1,
                                                "title": 1})
        for result in results:
            key = result["_id"]
            res_dict[key] = result["full_cn_str"]
            if "title" in result and result["title"]:
                res_dict["title_" + key] = result["title"]
        return res_dict

    def local_video_search(self, query_str, video_id, isSemantic=True):
        """

        :param query_str:
        :param video_id:
        :param isSemantic:
        :return res_dict:
        """
        res_dict = {}
        curr_key = 0
        inputs_dict = self.get_input_dict([video_id])
        bluE_results = bluE_standard(query_str, inputs_dict, lang='ch',
                                     isSemantic=isSemantic,
                                     max_size=10)
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
        """

        :param video_id:
        :param res_pos:
        :return:
        """
        res_charId_bg = int(res_pos[0])
        res_charId_ed = int(res_pos[1])
        result = self.database.video.find_one({"_id": video_id},
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
    """
    连接mongodb数据库
    :return database:
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
    client = MongoClient(host=mongodb_host, username=mongodb_user,
                         password=mongodb_password,
                         authSource=mongodb_db,
                         authMechanism=mongodb_authMechanism,
                         port=mongodb_port)
    database = client.get_database(mongodb_db)
    return database


def main():
    print('Start')
    print()
    ###### Sample One (Local Search) ######

    # video_ids = ['4339af28471e62289847391fab65b149']
    # query_str = '向量'

    # ss = time.time()
    # s = Search()
    # res_list = s.local_search(query_str, video_ids)

    # ee = time.time()

    # print('###### Sample One (Local Search) ######')
    # print('Query:',query_str)
    # pprint.pprint(res_list)
    # print('Video Size:',len(video_ids))
    # print('Time Cost: ', ee-ss)
    # print()

    ###### Sample Two (Global Search) ######

    video_ids = []
    query_str = '重力'

    ss = time.time()
    s = Search()
    type = 'all'
    max_size = 10
    page = 1
    res_list = s.global_search(query_str, video_ids, type, max_size, page)

    ee = time.time()

    print('###### Sample Two (Global Search) ######')
    print('Query:', query_str)
    pprint.pprint(res_list)
    print('Video Size:', len(video_ids))
    print('Time Cost: ', ee - ss)


if __name__ == "__main__":
    main()
