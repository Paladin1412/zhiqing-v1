# -*- coding: UTF-8 -*-
"""
 # Class UploadAttachedMediaRequest
 #
 # Aliyun VoD's Upload Attached Media(such as watermark,subtitle files) Request class, which wraps parameters to upload an media file into VoD.
 # Users could pass parameters to AliyunVodUploader, including File Path,Title,etc. via an UploadAttachedMediaRequest instance.
 # For more details, please check out the VoD API document: https://help.aliyun.com/document_detail/98467.html
"""

from utils.video_upload.voduploadsdk.AliyunVodUtils import *


class UploadAttachedMediaRequest:
    def __init__(self, filePath, businessType, title=None, fileExt=None):
        """
        constructor for UploadAttachedMediaRequest
        :param filePath: string, 文件的绝对路径，或者网络文件的URL，必须含有扩展名
        :return
        """
        self.businessType = businessType
        self.filePath = None
        self.fileName = None
        self.mediaExt = None
        self.title = None
        self.setFilePath(filePath, title, fileExt)

        self.fileSize = None
        self.cateId = None
        self.tags = None
        self.description = None
        self.userData = None
        self.storageLocation = None
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

    def setBusinessType(self, businessType):
        self.businessType = businessType

    def setTitle(self, title):
        self.title = title

    def setFileSize(self, fileSize):
        self.fileSize = fileSize

    def setCateId(self, cateId):
        self.cateId = cateId

    def setTags(self, tags):
        self.tags = tags

    def setDescription(self, description):
        self.description = description

    def setStorageLocation(self, storageLocation):
        self.storageLocation = storageLocation

    def setUserData(self, userData):
        self.userData = userData

    def setAppId(self, appId):
        self.appId = appId

    def setWorkflowId(self, workflowId):
        self.workflowId = workflowId
