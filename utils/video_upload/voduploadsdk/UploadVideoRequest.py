# -*- coding: UTF-8 -*-
"""
 # Class UploadVideoRequest
 #
 # Aliyun VoD's Upload Video Request class, which wraps parameters to upload a videos into VoD.
 # Users could pass parameters to AliyunVodUploader, including File Path,Title,etc. via an UploadVideoRequest instance.
 # For more details, please check out the VoD API document: https://help.aliyun.com/document_detail/55407.html
"""

from utils.video_upload.voduploadsdk.AliyunVodUtils import *


class UploadVideoRequest:
    def __init__(self, filePath, title=None, fileExt=None):
        """
        constructor for UploadVideoRequest
        :param filePath: string, 文件的绝对路径，或者网络文件的URL，必须含有扩展名
        :param title: string, 视频标题，最长128字节，不传则使用文件名为标题
        :return
        """
        self.filePath = None
        self.fileName = None
        self.mediaExt = None
        self.title = None
        self.setFilePath(filePath, title, fileExt)

        self.cateId = None
        self.tags = None
        self.description = None
        self.coverURL = None
        self.templateGroupId = None
        self.isShowWatermark = None
        self.userData = None
        self.storageLocation = None
        self.uploadId = None
        self.appId = None
        self.workflowId = None

    def setFilePath(self, filePath, title=None, fileExt=None):
        if fileExt is None:
            fileExt = AliyunVodUtils.getFileExtension(filePath)
            if not fileExt:
                raise AliyunVodException('ParameterError', 'InvalidParameter',
                                         'filePath has no Extension')

        fileExt = fileExt.lstrip('.')
        self.mediaExt = fileExt
        self.filePath = AliyunVodUtils.toUnicode(filePath)

        briefPath, briefName = AliyunVodUtils.getFileBriefPath(self.filePath)
        self.fileName = briefPath
        if fileExt and (not self.fileName.endswith('.' + fileExt)):
            self.fileName = self.fileName + '.' + fileExt

        if title:
            self.title = title
        else:
            if self.title is None:
                self.title = briefName

    def setCateId(self, cateId):
        self.cateId = cateId

    def setTags(self, tags):
        self.tags = tags

    def setDescription(self, description):
        self.description = description

    def setCoverURL(self, coverURL):
        self.coverURL = coverURL

    def setTemplateGroupId(self, templateGroupId):
        self.templateGroupId = templateGroupId

    # 关闭水印，仅用于配置全局水印且转码模板开启水印后，单次上传时关闭水印   
    def shutdownWatermark(self):
        self.isShowWatermark = False

    # 设置上传ID，可用于关联导入视频
    def setUploadId(self, uploadId):
        self.uploadId = uploadId

    def setAppId(self, appId):
        self.appId = appId

    def setWorkflowId(self, workflowId):
        self.workflowId = workflowId
