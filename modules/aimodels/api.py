from configparser import ConfigParser
from pymongo import MongoClient, ReadPreference

def connect_mongodb():
    '''

    :return database:
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
    client = MongoClient(host=mongodb_host, username=mongodb_user, password=mongodb_password,
                            authSource=mongodb_db, authMechanism=mongodb_authMechanism, port=mongodb_port)
    database = client.get_database(mongodb_db)
    return database

# 14.获取系列信息
def get_series(user_id):
    '''
    获取当前用户的系列信息
    :param user_id:
    :return res_data:
    '''
    database = connect_mongodb()
    series_collection = database.series
    results = series_collection.find({'user_id':user_id})
    res_data = []
    for result in results:
        data_dict = {'title':result['title']}
        res_data.append(data_dict)
    return res_data

# 2.视频播放
def video_play(video_id, user_id):
    '''
    获取视频播放页的信息,同时累加视频的播放量
    :param video_id:
    :param user_id:
    :return res_data:
    '''
    res_data = []
    database = connect_mongodb()
    tool = database.tool.find_one({'type':'category'})
    video = database.video.find_one({'_id':video_id})
    user = database.collection.find_one({"_id":user_id},{"name":1,"_id":1,"headshot":1})
    like_counts = database.like.find({"relation_id":video_id,"type":"video"}).count()
    comment_counts = database.comment.find({"video_id":video_id}).count()
    author_id = video['user_id']
    view_counts = 0 if 'view_counts' not in list(video.keys()) else video['view_counts']
    comment_list = []
    comments = database.comment.find({'video_id':video_id,'parent_id':{'$exists':False}})
    for comment in comments:
        # [todo]is_like的判断
        comment['is_like'] = 0
        comment_list.append(comment)
    data_dict = {}
    data_dict['video_id'] = video_id
    data_dict['video_path'] = video['video_path']
    data_dict['audio_path'] = video['audio_path']
    data_dict['lang'] = video['lang']
    data_dict['ass_path'] = video['ass_path']
    data_dict['upload_time'] = video['upload_time']
    data_dict['title'] = video['title']
    data_dict['comment'] = comment_list
    data_dict['user_id'] = user_id
    data_dict['user_name'] = user['name']
    data_dict['headshot'] = user['headshot']
    data_dict['category'] = tool['data'][video['category']]
    data_dict['lang'] = video['lang']
    data_dict['description'] = video['description']
    data_dict['image_path'] = video['image_path']
    data_dict['view_counts'] = video['view_counts']
    data_dict['like_counts'] = like_counts
    data_dict['comment_counts'] = comment_counts
    if user_id:
        like = database.like.find_one({'relation_id':video_id,'type':'video','user_id':user_id})
        collection = database.collection.find_one({'relation_id':video_id,'type':'video','user_id':user_id})
        subscription = database.subscription.find_one({'relation_id':author_id,'type':'author','user_id':user_id})
        data_dict['is_like'] = 1 if like else 0
        data_dict['is_collect'] = 1 if collection else 0
        data_dict['is_subscribe'] = 1 if subscription else 00
    res_data.append(data_dict)
    database.video.update_one({'_id':video_id},{'$set':{'view_counts':view_counts+1}})
    return res_data
