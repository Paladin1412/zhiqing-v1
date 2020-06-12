# -*- coding: utf-8 -*-
#


import json
import os
import pprint
import time
from configparser import ConfigParser

import requests
from pymongo import MongoClient


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


def jump_search(query_str, raw_source_str):
    res_list = []
    source_str = raw_source_str + '.' * (len(query_str) + 1)

    hasResult = True
    curr_source_str = source_str[:]
    abs_curr_index = 0

    while hasResult:
        try:
            curr_index = curr_source_str.index(query_str)
            abs_curr_index += curr_index + len(query_str)
            res_list.append([abs_curr_index - len(query_str), query_str])
            curr_source_str = curr_source_str[curr_index + len(query_str):]

        except:
            hasResult = False

    return res_list


def inHeur_search(raw_query_str, raw_source_str, inHeur_chars='的了呢呐呃嗯呀哦噢哈吗哇么',
                  split_chars=',.?!:;，。！？：；'):
    res_list = []
    source_str = raw_source_str[:]
    query_str = raw_query_str[:]

    for inHeur_char in inHeur_chars: query_str = query_str.replace(inHeur_char,
                                                                   '')

    if len(query_str) < len(raw_query_str) * 0.6: return []

    for cand_char in split_chars: source_str = source_str.replace(cand_char,
                                                                  '#')

    source_list = source_str.split('#')
    for source_item in source_list:
        inHeur_source_item = source_item[:]
        for inHeur_char in inHeur_chars: inHeur_source_item = inHeur_source_item.replace(
            inHeur_char, '')
        if query_str in inHeur_source_item and len(inHeur_source_item) > len(
                source_item) * 0.7:
            res_list.append([raw_source_str.index(source_item), source_item])

    return res_list


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

    def get_document(self, video_ids):
        """

        :return:
        """
        res_dict = {}
        map_dict = {}
        condition = {}
        if video_ids:
            condition = {"video_id": {"$in": video_ids}, "price": {"$gt": 0}}
        documents = self.database.document.find(condition,
                                                {'full_str': 1, '_id': 1,
                                                 'char_id_to_page_id': 1})
        for document in documents:
            key = document["_id"]
            res_dict[key] = document["full_str"].lower()
            map_dict[key] = document["char_id_to_page_id"]
        return res_dict, map_dict

    def document_search(self, query_str, video_ids):
        """

        :param query_str:
        :return:
        """
        res_list = []
        added_ids = []
        added_pages = []

        input_paragraph, map_dict = self.get_document(video_ids)
        bluE_results = bluE_standard(query_str, input_paragraph, lang='ch',
                                     isSemantic=0, max_size=100)

        for res_item in bluE_results:
            matched_id = res_item['key_id']
            if matched_id:
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
            res_dict[key] = series["title"].lower()
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
            res_dict[user['_id']] = user['name'].lower()
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

        existed_subs_pos = []

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

            if match_frame['subs_pos'] not in existed_subs_pos:
                existed_subs_pos.append(match_frame['subs_pos'])
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
        query_str = query_str.lower()
        tool = self.database.tool.find_one({'type': 'category'}).get("data")
        if not video_ids:
            videos = self.database.video.find({"state": 2}, {"_id": 1})
            for video in videos:
                video_ids.append(video["_id"])
        video_num = 0
        series_num = 0
        user_num = 0
        document_num = 0
        if search_range in ['video', 'all']:
            res_dict = self.video_search(query_str, video_ids, isBluE=isBluE)
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
                        for category_tool in tool:
                            if category_number == category_tool["id"]:
                                category.append(category_tool["name"])
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
                        compare[len(temp_data) - 1] = match_frame[video_id][
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
                        compare[len(temp_data) - 1] = user_dict[user_id][
                            'score']

        if search_range in ['series', 'all']:
            series_dict = self.series_search(query_str)
            for series_id in series_dict:
                if series_id:
                    series_num += 1
                    series = self.database.series.find_one({'_id': series_id})
                    category = []
                    for category_number in series['category']:
                        for category_number in result['category']:
                            for category_tool in tool:
                                if category_number == category_tool["id"]:
                                    category.append(category_tool["name"])
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
                    comment_counts = self.database.comment.find(
                        {"video_id": {'$in': video_ids}}).count()
                    video_counts = self.database.video.find(
                        {"series": series_id, "state": 2}).count()
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
                    data['update_time'] = series['time']
                    data['video_counts'] = video_counts
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
                        compare[len(temp_data) - 1] = series_dict[series_id][
                            'score']

        if search_range in ['document', 'all']:
            document_list = self.document_search(query_str, video_ids)
            if document_list:
                for document_dict in document_list:
                    document_num += 1
                    dict_search = {'source': 'document'}
                    data = dict_search['data'] = {}
                    document_id = document_dict['matched_id']
                    document = self.database.document.find_one(
                        {'_id': document_id},
                        {'file_name': 1, 'type': 1, 'download_counts': 1,
                         'time': 1})
                    data['file_id'] = document_id
                    data['file_name'] = document['file_name']
                    data['file_type'] = document['type']
                    data['time'] = document['time']
                    data['download_counts'] = document['download_counts']
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
                        compare[len(temp_data) - 1] = document_dict['score']

        compare_list = sorted(compare.items(), key=lambda x: x[1], reverse=True)
        for num in compare_list:
            result_data.append(temp_data[num[0]])

        unsorted_data = {}
        for _item in result_data[:]:
            if 'video_id' in _item['data']:
                unsorted_data[_item['data']['video_id']] = _item
            if 'document_id' in _item['data']:
                unsorted_data[_item['data']['document_id']] = _item

        sorted_ids = sorted(unsorted_data, key=lambda v: (
        unsorted_data[v]['match_frame']['score']), reverse=True)
        # print(sorted_ids)
        sorted_result_data = [unsorted_data[_id] for _id in sorted_ids]

        return sorted_result_data[max_size * (page - 1):max_size * page]

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

        # if not isBluE:
        #     for video_id in inputs_dict:
        #         curr_str = inputs_dict[video_id]
        #         if query_str in curr_str:
        #             matched_index = curr_str.index(query_str)
        #             res_dict[video_id] = {
        #                 'pos': [matched_index,
        #                         matched_index + len(query_str) + 1],
        #                 'matched_str': query_str
        #             }

        if isBluE:
            bluE_results = bluE_standard(query_str, inputs_dict, lang='ch',
                                         isSemantic=0,
                                         max_size=100)

            ###
            for video_id in inputs_dict:
                curr_str = inputs_dict[video_id]
                # jump_res = jump_search(query_str, curr_str)
                # inHeur_res = inHeur_search(query_str, inputs_dict[video_id])

                # if jump_res != []:
                #     for jump_item in jump_res:
                #         str_pos = [str(jump_item[0]), str(jump_item[0]+len(query_str))]

                if query_str in curr_str:
                    matched_index = curr_str.index(query_str)
                    res_dict[video_id] = {
                        'pos': [matched_index,
                                matched_index + len(query_str) + 1],
                        'matched_str': query_str,
                        'type': "subtitle",
                        'score': 1.0
                    }

                inHeur_res = inHeur_search(query_str, curr_str)
                if inHeur_res != []:
                    inHeur_item = inHeur_res[0]
                    str_pos = [str(inHeur_item[0]),
                               str(inHeur_item[0] + len(inHeur_item[1]))]
                    res_dict[video_id] = {
                        'pos': str_pos,
                        'matched_str': inHeur_item[1],
                        'type': "subtitle",
                        'score': 1.0
                    }

            # print('xsxsxs')
            # pprint.pprint(bluE_results[:5])

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
            res_dict[result["_id"]] = result["full_cn_str"].lower()
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
            res_dict[key] = result["full_cn_str"].lower()
            if "title" in result and result["title"]:
                res_dict["title_" + key] = result["title"].lower()
        return res_dict

    def local_video_search(self, query_str, video_id, isSemantic=True):
        """

        :param query_str:
        :param video_id:
        :param isSemantic:
        :return res_dict:
        """
        LOCAL_MAX_SIZE = 10

        res_dict = {}
        curr_key = 0
        inputs_dict = self.get_input_dict([video_id])
        bluE_results = bluE_standard(query_str, inputs_dict, lang='ch',
                                     isSemantic=isSemantic,
                                     max_size=LOCAL_MAX_SIZE)

        jump_res = jump_search(query_str, inputs_dict[video_id])
        inHeur_res = inHeur_search(query_str, inputs_dict[video_id])

        if jump_res != []:
            for jump_item in jump_res:
                str_pos = [str(jump_item[0]),
                           str(jump_item[0] + len(query_str))]
                if curr_key < LOCAL_MAX_SIZE:
                    res_dict[curr_key] = {
                        'video_id': video_id,
                        'pos': str_pos,
                        'matched_str': query_str
                    }
                    curr_key += 1

        if jump_res == [] and inHeur_res != []:
            for inHeur_item in inHeur_res:
                str_pos = [str(inHeur_item[0]),
                           str(inHeur_item[0] + len(inHeur_item[1]))]
                if curr_key < LOCAL_MAX_SIZE:
                    res_dict[curr_key] = {
                        'video_id': video_id,
                        'pos': str_pos,
                        'matched_str': inHeur_item[1]
                    }
                    curr_key += 1

        for item in bluE_results:
            str_pos = item['str_position']
            # toDo generating multiple results
            if curr_key < LOCAL_MAX_SIZE:
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

    video_ids = ['c918a902b296a38feaa7e4af0a0ee901']
    query_str = '向量的大小'

    ss = time.time()
    s = Search()
    res_list = s.local_search(query_str, video_ids)

    ee = time.time()

    print('###### Sample One (Local Search) ######')
    print('Query:', query_str)
    pprint.pprint(res_list)
    print('Video Size:', len(video_ids))
    print('Time Cost: ', ee - ss)
    print()

    ###### Sample Two (Global Search) ######

    # video_ids = ["9bedd89faf371092e1aaaacf5fd3b704",
    #              "162fb70b08169805aab916f75711b015",
    #              "5c82d69504419c65f4aec21db403e904",
    #              "4339af28471e62289847391fab65b149",
    #              "ee73aca89fb3c23397f55f5db9f8db03",
    #              "c918a902b296a38feaa7e4af0a0ee901"]

    # video_ids = []
    # # query_str = '向量的加法'
    # query_str = '财政自由'
    # # query_str = ''

    # ss = time.time()
    # s = Search()
    # type = 'document'
    # max_size = 5
    # page = 1
    # res_list = s.global_search(query_str, video_ids, type, max_size, page)

    # ee = time.time()

    # print('###### Sample Two (Global Search) ######')
    # print('Query:', query_str)
    # pprint.pprint(res_list)
    # print('Video Size:', len(video_ids))
    # print('Time Cost: ', ee - ss)


if __name__ == "__main__":
    main()
