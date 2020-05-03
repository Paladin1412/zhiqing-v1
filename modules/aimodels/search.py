import json
import os
from configparser import ConfigParser

import requests
from pymongo import MongoClient, ReadPreference


class Search:
    def __init__(self):
        database = connect_mongodb()
        self.video_collection = database.video

    def video_search(self, query_str, video_ids, mode='global', isBluE=True,
                     isSemantic=True):

        result_data = []
        match_frame = {}
        match_ids = []
        if mode == 'global':
            if not video_ids:
                results = self.video_collection.find({"state": 2}, {"_id": 1})
                for result in results:
                    video_ids.append(result["_id"])
            if query_str:
                res_dict = self.global_search(query_str, video_ids,
                                              isBluE=isBluE)
                for video_id in res_dict:
                    char_dur, time_dur = self.result_transformer(video_id,
                                                                 res_dict[
                                                                     video_id][
                                                                     'pos'])
                    match_frame[video_id] = {
                        "matched_sub": res_dict[video_id]['matched_str'],
                        "start_time": time_dur[0],
                        "end_time": time_dur[1],
                        "subs_pos": char_dur,
                        "video_id": video_id}
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
                    dict_search['video_path'] = {"720P": result['video_path']}
                    dict_search['audio_path'] = result['audio_path']
                    dict_search['lang'] = result['lang']
                    dict_search['subtitling'] = result['subtitling']
                    dict_search['upload_date'] = result['date']
                    dict_search['category'] = result['category']
                    # dict_search['image_path'] = result['image_path']
                    # dict_search['webvtt'] = result['webvtt']
                    if query_str:
                        dict_search['match_frame'] = match_frame[result['_id']]
                    result_data.append(dict_search)
        if mode == 'local':
            res_dict = self.local_search(query_str, video_ids[0],
                                         isSemantic=isSemantic)
            for video_id in res_dict:
                char_dur, time_dur = self.result_transformer(video_id,
                                                             res_dict[video_id][
                                                                 'pos'])
                match_frame = {
                    "matched_sub": res_dict[video_id]['matched_str'],
                    "start_time": time_dur[0],
                    "end_time": time_dur[1],
                    "subs_pos": char_dur,
                    "video_id": video_id}
            dict_search = {}
            dict_search['match_frame'] = match_frame
            result_data.append(dict_search)

        return result_data

    def global_search(self, query_str, video_ids, isBluE=False):

        inputs_dict = self.get_input_dict(video_ids)

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
                                              isSemantic=0,
                                              max_size=100)
            for item in bluE_results:
                curr_key = item['key_id']
                str_pos = item['str_position']
                if curr_key not in res_dict:
                    res_dict[curr_key] = {
                        'pos': str_pos,
                        'matched_str': item['matched_str']
                    }

        return res_dict

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
        inputs_dict = self.get_input_dict([video_id])
        bluE_results = self.bluE_standard(query_str, inputs_dict, lang='ch',
                                          isSemantic=isSemantic,
                                          max_size=10)

        for item in bluE_results:
            curr_key = item['key_id']
            str_pos = item['str_position']
            # toDo generating multiple results
            if curr_key not in res_dict:
                res_dict[curr_key] = {
                    'pos': str_pos,
                    'matched_str': item['matched_str']
                }

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
    mongodb_port = int(parser.get('mongodb', 'port'))
    mongodb_user = parser.get('mongodb', 'user')
    mongodb_password = parser.get('mongodb', 'password')
    mongodb_authMechanism = parser.get('mongodb', 'authMechanism')
    client = MongoClient(mongodb_host, username=mongodb_user,
                         password=mongodb_password,
                         authSource=mongodb_db,
                         authMechanism=mongodb_authMechanism,
                         read_preference=ReadPreference.SECONDARY_PREFERRED,
                         port=mongodb_port)
    # client = MongoClient(host='127.0.0.1', port=27017)
    database = client.get_database(mongodb_db)
    return database
