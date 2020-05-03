# -*- coding: UTF-8 -*-
from utils import response_code
from config.settings import config
from .voduploadsdk.AliyunVodUtils import *
from .voduploadsdk.UploadVideoRequest import UploadVideoRequest
from .voduploadsdk.VodUploader import vodUploader

video_host = 'http://videos.haetek.com'


def upload_local_video(accessKeyId, accessKeySecret, file_path,
                       file_title="", file_tags="", file_desc="",
                       storageLocation=None):
    try:
        uploader = vodUploader(accessKeyId, accessKeySecret)
        uploadVideoRequest = UploadVideoRequest(file_path, file_title)
        uploadVideoRequest.setTags(file_tags)
        uploadVideoRequest.setDescription(file_desc)
        if storageLocation:
            uploadVideoRequest.setStorageLocation(storageLocation)
        # videoId = uploader.uploadLocalVideo(uploadVideoRequest)
        upload_info = uploader.uploadLocalVideo(uploadVideoRequest)
        # pprint(vars(uploadVideoRequest))
        upload_address = upload_info['UploadAddress']
        video_url = "{}/{}".format(video_host, upload_address['FileName'])
        # print(uploadInfo['UploadAddress'], uploadInfo['MediaId'])
        # print(video_url)
        return {'video_url': video_url,
                'media_id': upload_info['MediaId'],
                'from_file': file_path,
                'upload_info': upload_info}

        # print("file: %s, videoId: %s " % (uploadVideoRequest.filePath, uploadInfo['MediaId']))

    except AliyunVodException as e:
        print("上传视频失败了———— {}".format(e))
        raise response_code.ThirdERR(errmsg="上传视频失败了———— {}".format(e))
        logger.error("filePath: {} exception: {}".format(file_path, e))


# 上传网络视频
def upload_web_video(accessKeyId, accessKeySecret, fileUrl,
                     storageLocation=None):
    try:
        uploader = vodUploader(accessKeyId, accessKeySecret)
        uploadVideoRequest = UploadVideoRequest(fileUrl,
                                                'test upload web videos')
        uploadVideoRequest.setTags('ai')
        if storageLocation:
            uploadVideoRequest.setStorageLocation(storageLocation)
        upload_info = uploader.uploadWebVideo(uploadVideoRequest)
        # print("file: %s, videoId: %s" % (uploadVideoRequest.filePath, videoId))
        upload_address = upload_info['UploadAddress']
        video_url = "{}/{}".format(video_host, upload_address['FileName'])
        # print(uploadInfo['UploadAddress'], uploadInfo['MediaId'])
        # print(video_url)
        return {'video_url': video_url,
                'media_id': upload_info['MediaId'],
                'from_file': fileUrl,
                'upload_info': upload_info}

    except AliyunVodException as e:
        print(e)


# def main(local_file='/apps/docker_containers/nginx/data/videos/unique_id1.mp4'):
def upload_video(file_path, file_title='', file_tags='', file_desc=''):
    res = upload_local_video(accessKeyId=config.UPLOAD_ACCESS_ID,
                             accessKeySecret=config.UPLOAD_ACCESS_ID_SECRET,
                             file_path=file_path, file_title=file_title,
                             file_tags=file_tags, file_desc=file_desc)
    logger.info(res)
    # pprint(res)
    return res


if __name__ == '__main__':
    upload_video()
