# -*- coding: UTF-8 -*-
import base64
import json
import time

import oss2
from aliyunsdkcore import client
from aliyunsdkvod.request.v20170321 import CreateUploadAttachedMediaRequest
from aliyunsdkvod.request.v20170321 import CreateUploadImageRequest
from aliyunsdkvod.request.v20170321 import CreateUploadVideoRequest
from aliyunsdkvod.request.v20170321 import RefreshUploadVideoRequest

from utils.video_upload.voduploadsdk.AliyunVodUtils import *

VOD_MAX_TITLE_LENGTH = 128
VOD_MAX_DESCRIPTION_LENGTH = 1024


class vodUploader:

    def __init__(self, accessKeyId, accessKeySecret, ecsRegionId=None):
        """
        constructor for VodUpload
        :param accessKeyId: string, access key id
        :param accessKeySecret: string, access key secret
        :param ecsRegion: string, 部署迁移脚本的ECS所在的Region，详细参考：https://help.aliyun.com/document_detail/40654.html，如：cn-beijing
        :return
        """
        self.__accessKeyId = accessKeyId
        self.__accessKeySecret = accessKeySecret
        self.__ecsRegion = ecsRegionId
        self.__vodApiRegion = None
        self.__connTimeout = 3
        self.__bucketClient = None
        self.__maxRetryTimes = 3
        self.__vodClient = None
        self.__EnableCrc = True

        # 分片上传参数
        self.__multipartThreshold = 10 * 1024 * 1024  # 分片上传的阈值，超过此值开启分片上传
        self.__multipartPartSize = 10 * 1024 * 1024  # 分片大小，单位byte
        self.__multipartThreadsNum = 3  # 分片上传时并行上传的线程数，暂时为串行上传，不支持并行，后续会支持。

        self.setApiRegion('cn-shanghai')

    def setApiRegion(self, apiRegion):
        """
        设置VoD的接入地址，中国大陆为cn-shanghai，海外支持ap-southeast-1(新加坡)等区域，详情参考：https://help.aliyun.com/document_detail/98194.html
        :param apiRegion: 接入地址的Region英文表示
        :return:
        """
        self.__vodApiRegion = apiRegion
        self.__vodClient = self.__initVodClient()

    def setMultipartUpload(self, multipartThreshold=10 * 1024 * 1024,
                           multipartPartSize=10 * 1024 * 1024,
                           multipartThreadsNum=1):
        if multipartThreshold > 0:
            self.__multipartThreshold = multipartThreshold
        if multipartPartSize > 0:
            self.__multipartPartSize = multipartPartSize
        if multipartThreadsNum > 0:
            self.__multipartThreadsNum = multipartThreadsNum

    def setEnableCrc(self, isEnable=False):
        self.__EnableCrc = True if isEnable else False

    @catch_error
    def uploadLocalVideo(self, uploadVideoRequest, startUploadCallback=None):
        """
        上传本地视频或音频文件到点播，最大支持48.8TB的单个文件，暂不支持断点续传
        :param uploadVideoRequest: UploadVideoRequest类的实例，注意filePath为本地文件的绝对路径
        :param startUploadCallback为获取到上传地址和凭证(uploadInfo)后开始进行文件上传时的回调，可用于记录上传日志等；uploadId为设置的上传ID，可用于关联导入视频。
        :return
        """
        uploadInfo = self.__createUploadVideo(uploadVideoRequest)
        # print(uploadInfo)
        if startUploadCallback:
            startUploadCallback(uploadVideoRequest.uploadId, uploadInfo)
        headers = self.__getUploadHeaders(uploadVideoRequest)
        self.__uploadOssObjectWithRetry(uploadVideoRequest.filePath,
                                        uploadInfo['UploadAddress']['FileName'],
                                        uploadInfo,
                                        headers)
        # return uploadInfo['VideoId']
        return uploadInfo

    @catch_error
    def uploadWebVideo(self, uploadVideoRequest, startUploadCallback=None):
        """
        上传网络视频或音频文件到点播，最大支持48.8TB的单个文件(需本地磁盘空间足够)；会先下载到本地临时目录，再上传到点播存储
        :param uploadVideoRequest: UploadVideoRequest类的实例，注意filePath为网络文件的URL地址
        :return
        """
        # 下载文件
        uploadVideoRequest = self.__downloadWebMedia(uploadVideoRequest)

        # 上传到点播
        uploadInfo = self.__createUploadVideo(uploadVideoRequest)
        if startUploadCallback:
            startUploadCallback(uploadVideoRequest.uploadId, uploadInfo)
        headers = self.__getUploadHeaders(uploadVideoRequest)
        self.__uploadOssObjectWithRetry(uploadVideoRequest.filePath,
                                        uploadInfo['UploadAddress']['FileName'],
                                        uploadInfo,
                                        headers)

        # 删除本地临时文件
        os.remove(uploadVideoRequest.filePath)

        # return uploadInfo['VideoId']
        return uploadInfo

    @catch_error
    def uploadLocalM3u8(self, uploadVideoRequest, sliceFilePaths=None):
        """
        上传本地m3u8视频或音频文件到点播，m3u8文件和分片文件默认在同一目录
        :param uploadVideoRequest: UploadVideoRequest类的实例，注意filePath为本地m3u8索引文件的绝对路径，
              且m3u8文件的分片信息必须是相对地址，不能含有URL或本地绝对路径
        :param sliceFilePaths: list, 分片文件的本地路径列表，例如：['/opt/m3u8_video/sample_001.ts', '/opt/m3u8_video/sample_002.ts']
              sliceFilePaths为None时，会按照同一目录去解析分片地址；如不在同一目录等原因导致解析有误，可自行组装分片地址
        :return
        """

        if sliceFilePaths is None:
            sliceFilePaths = self.parseLocalM3u8(uploadVideoRequest.filePath)

        if (not isinstance(sliceFilePaths, list)) or len(sliceFilePaths) <= 0:
            raise AliyunVodException('InvalidM3u8SliceFile',
                                     'M3u8 slice files invalid',
                                     'sliceFilePaths invalid or m3u8 index file error')

        # 上传到点播的m3u8索引文件会重写，以此确保分片地址都为相对地址
        downloader = AliyunVodDownloader()
        m3u8LocalDir = downloader.getSaveLocalDir() + '/' + AliyunVodUtils.getStringMd5(
            uploadVideoRequest.fileName)
        downloader.setSaveLocalDir(m3u8LocalDir)
        m3u8LocalPath = m3u8LocalDir + '/' + os.path.basename(
            uploadVideoRequest.fileName)
        self.__rewriteM3u8File(uploadVideoRequest.filePath, m3u8LocalPath, True)

        # 获取上传凭证
        uploadVideoRequest.setFilePath(m3u8LocalPath)
        uploadInfo = self.__createUploadVideo(uploadVideoRequest)
        uploadAddress = uploadInfo['UploadAddress']
        headers = self.__getUploadHeaders(uploadVideoRequest)

        # 依次上传分片文件
        for sliceFilePath in sliceFilePaths:
            tempFilePath, sliceFileName = AliyunVodUtils.getFileBriefPath(
                sliceFilePath)
            self.__uploadOssObjectWithRetry(sliceFilePath,
                                            uploadAddress[
                                                'ObjectPrefix'] + sliceFileName,
                                            uploadInfo, headers)

        # 上传m3u8文件
        self.__uploadOssObjectWithRetry(m3u8LocalPath,
                                        uploadAddress['FileName'], uploadInfo,
                                        headers)

        # 删除重写到本地的m3u8文件
        if os.path.exists(m3u8LocalPath):
            os.remove(m3u8LocalPath)
        if not os.listdir(m3u8LocalDir):
            os.rmdir(m3u8LocalDir)

        return uploadInfo['VideoId']

    @catch_error
    def uploadWebM3u8(self, uploadVideoRequest, sliceFileUrls=None):
        """
        上传网络m3u8视频或音频文件到点播，需本地磁盘空间足够，会先下载到本地临时目录，再上传到点播存储
        :param uploadVideoRequest: UploadVideoRequest类的实例，注意filePath为m3u8网络文件的URL地址
        :param sliceFileUrls: list, 分片文件的url，例如：['http://host/sample_001.ts', 'http://host/sample_002.ts']
            sliceFileUrls为None时，会按照同一前缀解析分片地址；如分片路径和m3u8索引文件前缀不同等原因导致解析有误，可自行组装分片地址
        :return
        """
        if sliceFileUrls is None:
            sliceFileUrls = self.parseWebM3u8(uploadVideoRequest.filePath)

        if (not isinstance(sliceFileUrls, list)) or len(sliceFileUrls) <= 0:
            raise AliyunVodException('InvalidM3u8SliceFile',
                                     'M3u8 slice urls invalid',
                                     'sliceFileUrls invalid or m3u8 index file error')

        # 下载m3u8文件和所有ts分片文件到本地；上传到点播的m3u8索引文件会重写，以此确保分片地址都为相对地址
        downloader = AliyunVodDownloader()
        m3u8LocalDir = downloader.getSaveLocalDir() + '/' + AliyunVodUtils.getStringMd5(
            uploadVideoRequest.fileName)
        downloader.setSaveLocalDir(m3u8LocalDir)
        m3u8LocalPath = m3u8LocalDir + '/' + os.path.basename(
            uploadVideoRequest.fileName)
        self.__rewriteM3u8File(uploadVideoRequest.filePath, m3u8LocalPath,
                               False)

        sliceList = []
        for sliceFileUrl in sliceFileUrls:
            tempFilePath, sliceFileName = AliyunVodUtils.getFileBriefPath(
                sliceFileUrl)
            err, sliceLocalPath = downloader.downloadFile(sliceFileUrl,
                                                          sliceFileName)
            if sliceLocalPath is None:
                raise AliyunVodException('FileDownloadError',
                                         'Download M3u8 File Error', '')
            sliceList.append((sliceLocalPath, sliceFileName))

        # 获取上传凭证
        uploadVideoRequest.setFilePath(m3u8LocalPath)
        uploadInfo = self.__createUploadVideo(uploadVideoRequest)
        uploadAddress = uploadInfo['UploadAddress']
        headers = self.__getUploadHeaders(uploadVideoRequest)

        # 依次上传分片文件
        for sliceFile in sliceList:
            self.__uploadOssObjectWithRetry(sliceFile[0],
                                            uploadAddress['ObjectPrefix'] +
                                            sliceFile[1],
                                            uploadInfo, headers)

        # 上传m3u8文件
        self.__uploadOssObjectWithRetry(m3u8LocalPath,
                                        uploadAddress['FileName'], uploadInfo,
                                        headers)

        # 删除下载到本地的m3u8文件和分片文件
        if os.path.exists(m3u8LocalPath):
            os.remove(m3u8LocalPath)
        for sliceFile in sliceList:
            if os.path.exists(sliceFile[0]):
                os.remove(sliceFile[0])
        if not os.listdir(m3u8LocalDir):
            os.rmdir(m3u8LocalDir)

        return uploadInfo['VideoId']

    @catch_error
    def uploadImage(self, uploadImageRequest, isLocalFile=True):
        """
        上传图片文件到点播，不支持断点续传；该接口可支持上传本地图片或网络图片
        :param uploadImageRequest: UploadImageRequest，注意filePath为本地文件的绝对路径或网络文件的URL地址
        :param isLocalFile: bool, 是否为本地文件。True：本地文件，False：网络文件
        :return
        """
        # 网络图片需要先下载到本地
        if not isLocalFile:
            uploadImageRequest = self.__downloadWebMedia(uploadImageRequest)

        # 上传到点播
        uploadInfo = self.__createUploadImage(uploadImageRequest)
        self.__uploadOssObject(uploadImageRequest.filePath,
                               uploadInfo['UploadAddress']['FileName'],
                               uploadInfo, None)

        # 删除本地临时文件
        if not isLocalFile:
            os.remove(uploadImageRequest.filePath)

        return uploadInfo['ImageId'], uploadInfo['ImageURL']

    @catch_error
    def uploadAttachedMedia(self, uploadAttachedRequest, isLocalFile=True):
        """
        上传辅助媒资文件(如水印、字幕文件)到点播，不支持断点续传；该接口可支持上传本地或网络文件
        :param uploadAttachedRequest: UploadAttachedMediaRequest，注意filePath为本地文件的绝对路径或网络文件的URL地址
        :param isLocalFile: bool, 是否为本地文件。True：本地文件，False：网络文件
        :return
        """
        # 网络文件需要先下载到本地
        if not isLocalFile:
            uploadAttachedRequest = self.__downloadWebMedia(
                uploadAttachedRequest)

        # 上传到点播
        uploadInfo = self.__createUploadAttachedMedia(uploadAttachedRequest)
        self.__uploadOssObject(uploadAttachedRequest.filePath,
                               uploadInfo['UploadAddress']['FileName'],
                               uploadInfo, None)

        # 删除本地临时文件
        if not isLocalFile:
            os.remove(uploadAttachedRequest.filePath)

        result = {'MediaId': uploadInfo['MediaId'],
                  'MediaURL': uploadInfo['MediaURL'],
                  'FileURL': uploadInfo['FileURL']}
        return result

    @catch_error
    def parseWebM3u8(self, m3u8FileUrl):
        """
        解析网络m3u8文件得到所有分片文件地址，原理是将m3u8地址前缀拼接ts分片名称作为后者的下载url，适用于url不带签名或分片与m3u8文件签名相同的情况
        本函数解析时会默认分片文件和m3u8文件位于同一目录，如不是则请自行拼接分片文件的地址列表
        :param m3u8FileUrl: string, m3u8网络文件url，例如：http://host/sample.m3u8
        :return sliceFileUrls
        """
        sliceFileUrls = []
        res = requests.get(m3u8FileUrl)
        res.raise_for_status()
        for line in res.iter_lines():
            if line.startswith('#'):
                continue
            sliceFileUrl = AliyunVodUtils.replaceFileName(m3u8FileUrl,
                                                          line.strip())
            sliceFileUrls.append(sliceFileUrl)

        return sliceFileUrls

    @catch_error
    def parseLocalM3u8(self, m3u8FilePath):
        """
        解析本地m3u8文件得到所有分片文件地址，原理是将m3u8地址前缀拼接ts分片名称作为后者的本地路径
        本函数解析时会默认分片文件和m3u8文件位于同一目录，如不是则请自行拼接分片文件的地址列表
        :param m3u8FilePath: string, m3u8本地文件路径，例如：/opt/videos/sample.m3u8
        :return sliceFilePaths
        """
        sliceFilePaths = []
        m3u8FilePath = AliyunVodUtils.toUnicode(m3u8FilePath)
        for line in open(m3u8FilePath):
            if line.startswith('#'):
                continue
            sliceFileName = line.strip()
            sliceFilePath = AliyunVodUtils.replaceFileName(m3u8FilePath,
                                                           sliceFileName)
            sliceFilePaths.append(sliceFilePath)

        return sliceFilePaths

    # 定义进度条回调函数；consumedBytes: 已经上传的数据量，totalBytes：总数据量
    def uploadProgressCallback(self, consumedBytes, totalBytes):

        if totalBytes:
            rate = int(100 * (float(consumedBytes) / float(totalBytes)))
        else:
            rate = 0

        print("[%s]uploaded %s bytes, percent %s%s" % (
            AliyunVodUtils.getCurrentTimeStr(), consumedBytes, format(rate),
            '%'))
        sys.stdout.flush()

    def __initVodClient(self):
        return client.AcsClient(self.__accessKeyId, self.__accessKeySecret,
                                self.__vodApiRegion,
                                auto_retry=True,
                                max_retry_time=self.__maxRetryTimes,
                                timeout=self.__connTimeout)

    def __downloadWebMedia(self, request):

        # 下载媒体文件到本地临时目录
        downloader = AliyunVodDownloader()
        localFileName = "%s.%s" % (
        AliyunVodUtils.getStringMd5(request.fileName), request.mediaExt)
        fileUrl = request.filePath
        err, localFilePath = downloader.downloadFile(fileUrl, localFileName)
        if err < 0:
            raise AliyunVodException('FileDownloadError', 'Download File Error',
                                     '')

        # 重新设置上传请求对象
        request.setFilePath(localFilePath)
        return request

    def __rewriteM3u8File(self, srcM3u8File, dstM3u8File, isSrcLocal=True):
        newM3u8Text = ''
        if isSrcLocal:
            for line in open(AliyunVodUtils.toUnicode(srcM3u8File)):
                item = self.__processM3u8Line(line)
                if item is not None:
                    newM3u8Text += item + "\n"
        else:
            res = requests.get(srcM3u8File)
            res.raise_for_status()
            for line in res.iter_lines():
                item = self.__processM3u8Line(line)
                if item is not None:
                    newM3u8Text += item + "\n"

        AliyunVodUtils.mkDir(dstM3u8File)
        with open(dstM3u8File, 'w') as f:
            f.write(newM3u8Text)

    def __processM3u8Line(self, line):
        item = line.strip()
        if len(item) <= 0:
            return None

        if item.startswith('#'):
            return item

        tempFilePath, fileName = AliyunVodUtils.getFileBriefPath(item)
        return fileName

    def __requestUploadInfo(self, request, mediaType):
        request.set_accept_format('JSON')
        result = json.loads(
            self.__vodClient.do_action_with_exception(request).decode('utf-8'))
        result['OriUploadAddress'] = result['UploadAddress']
        result['OriUploadAuth'] = result['UploadAuth']

        result['UploadAddress'] = json.loads(
            base64.b64decode(result['OriUploadAddress']).decode('utf-8'))
        result['UploadAuth'] = json.loads(
            base64.b64decode(result['OriUploadAuth']).decode('utf-8'))

        result['MediaType'] = mediaType
        if mediaType == 'videos':
            result['MediaId'] = result['VideoId']
        elif mediaType == 'image':
            result['MediaId'] = result['ImageId']
            result['MediaURL'] = result['ImageURL']

        return result

    # 获取视频上传地址和凭证
    def __createUploadVideo(self, uploadVideoRequest):
        request = CreateUploadVideoRequest.CreateUploadVideoRequest()

        title = AliyunVodUtils.subString(uploadVideoRequest.title,
                                         VOD_MAX_TITLE_LENGTH)
        request.set_Title(title)
        request.set_FileName(uploadVideoRequest.fileName)

        if uploadVideoRequest.description:
            description = AliyunVodUtils.subString(
                uploadVideoRequest.description,
                VOD_MAX_DESCRIPTION_LENGTH)
            request.set_Description(description)
        if uploadVideoRequest.coverURL:
            request.set_CoverURL(uploadVideoRequest.coverURL)
        if uploadVideoRequest.tags:
            request.set_Tags(uploadVideoRequest.tags)
        if uploadVideoRequest.cateId:
            request.set_CateId(uploadVideoRequest.cateId)
        if uploadVideoRequest.templateGroupId:
            request.set_TemplateGroupId(uploadVideoRequest.templateGroupId)
        if uploadVideoRequest.storageLocation:
            request.set_StorageLocation(uploadVideoRequest.storageLocation)
        if uploadVideoRequest.userData:
            request.set_UserData(uploadVideoRequest.userData)
        if uploadVideoRequest.appId:
            request.set_AppId(uploadVideoRequest.appId)
        if uploadVideoRequest.workflowId:
            request.set_WorkflowId(uploadVideoRequest.workflowId)

        result = self.__requestUploadInfo(request, 'videos')
        logger.info("CreateUploadVideo, FilePath: %s, VideoId: %s" % (
            uploadVideoRequest.filePath, result['VideoId']))
        return result

    # 刷新上传凭证
    def __refresh_upload_video(self, videoId):
        request = RefreshUploadVideoRequest.RefreshUploadVideoRequest();
        request.set_VideoId(videoId)

        result = self.__requestUploadInfo(request, 'videos')
        logger.info("RefreshUploadVideo, VideoId %s" % (result['VideoId']))
        return result

    # 获取图片上传地址和凭证
    def __createUploadImage(self, uploadImageRequest):
        request = CreateUploadImageRequest.CreateUploadImageRequest()

        request.set_ImageType(uploadImageRequest.imageType)
        request.set_ImageExt(uploadImageRequest.imageExt)
        if uploadImageRequest.title:
            title = AliyunVodUtils.subString(uploadImageRequest.title,
                                             VOD_MAX_TITLE_LENGTH)
            request.set_Title(title)
        if uploadImageRequest.description:
            description = AliyunVodUtils.subString(
                uploadImageRequest.description,
                VOD_MAX_DESCRIPTION_LENGTH)
            request.set_Description(description)
        if uploadImageRequest.tags:
            request.set_Tags(uploadImageRequest.tags)
        if uploadImageRequest.cateId:
            request.set_CateId(uploadImageRequest.cateId)
        if uploadImageRequest.storageLocation:
            request.set_StorageLocation(uploadImageRequest.storageLocation)
        if uploadImageRequest.userData:
            request.set_UserData(uploadImageRequest.userData)
        if uploadImageRequest.appId:
            request.set_AppId(uploadImageRequest.appId)
        if uploadImageRequest.workflowId:
            request.set_WorkflowId(uploadImageRequest.workflowId)

        result = self.__requestUploadInfo(request, 'image')
        logger.info(
            "CreateUploadImage, FilePath: %s, ImageId: %s, ImageUrl: %s" % (
                uploadImageRequest.filePath, result['ImageId'],
                result['ImageURL']))
        return result

    def __createUploadAttachedMedia(self, uploadAttachedRequest):
        request = CreateUploadAttachedMediaRequest.CreateUploadAttachedMediaRequest()
        request.set_BusinessType(uploadAttachedRequest.businessType)
        request.set_MediaExt(uploadAttachedRequest.mediaExt)

        if uploadAttachedRequest.title:
            title = AliyunVodUtils.subString(uploadAttachedRequest.title,
                                             VOD_MAX_TITLE_LENGTH)
            request.set_Title(title)
        if uploadAttachedRequest.description:
            description = AliyunVodUtils.subString(
                uploadAttachedRequest.description,
                VOD_MAX_DESCRIPTION_LENGTH)
            request.set_Description(description)
        if uploadAttachedRequest.tags:
            request.set_Tags(uploadAttachedRequest.tags)
        if uploadAttachedRequest.cateId:
            request.set_CateId(uploadAttachedRequest.cateId)
        if uploadAttachedRequest.storageLocation:
            request.set_StorageLocation(uploadAttachedRequest.storageLocation)
        if uploadAttachedRequest.userData:
            request.set_UserData(uploadAttachedRequest.userData)
        if uploadAttachedRequest.appId:
            request.set_AppId(uploadAttachedRequest.appId)
        if uploadAttachedRequest.workflowId:
            request.set_WorkflowId(uploadAttachedRequest.workflowId)

        result = self.__requestUploadInfo(request, 'attached')
        logger.info(
            "CreateUploadImage, FilePath: %s, MediaId: %s, MediaURL: %s" % (
                uploadAttachedRequest.filePath, result['MediaId'],
                result['MediaURL']))
        return result

    def __getUploadHeaders(self, uploadVideoRequest):
        if uploadVideoRequest.isShowWatermark is None:
            return None
        else:
            userData = "{\"Vod\":{\"UserData\":{\"IsShowWaterMark\": \"%s\"}}}" % (
                uploadVideoRequest.isShowWatermark)
            return {'x-oss-notification': base64.b64encode(userData, 'utf-8')}

    # uploadType，可选：multipart, put, web
    def __uploadOssObjectWithRetry(self, filePath, object, uploadInfo,
                                   headers=None):
        retryTimes = 0
        while retryTimes < self.__maxRetryTimes:
            try:
                return self.__uploadOssObject(filePath, object, uploadInfo,
                                              headers)
            except OssError as e:
                # 上传凭证过期需要重新获取凭证
                if e.code == 'SecurityTokenExpired' or e.code == 'InvalidAccessKeyId':
                    uploadInfo = self.__refresh_upload_video(
                        uploadInfo['MediaId'])
            except Exception as e:
                raise e
            except:
                raise AliyunVodException('UnkownError', repr(e),
                                         traceback.format_exc())
            finally:
                retryTimes += 1

    def __uploadOssObject(self, filePath, object, uploadInfo, headers=None):
        self.__createOssClient(uploadInfo['UploadAuth'],
                               uploadInfo['UploadAddress'])
        """
        p = os.path.dirname(os.path.realpath(__file__))
        store = os.path.dirname(p) + '/osstmp'
        return oss2.resumable_upload(self.__bucketClient, object, filePath,
                              store=oss2.ResumableStore(root=store), headers=headers,
                              multipart_threshold=self.__multipartThreshold, part_size=self.__multipartPartSize,
                              num_threads=self.__multipartThreadsNum, progress_callback=self.uploadProgressCallback)
        """
        uploader = _VodResumableUploader(self.__bucketClient, filePath, object,
                                         uploadInfo, headers,
                                         self.uploadProgressCallback,
                                         self.__refreshUploadAuth)
        uploader.setMultipartInfo(self.__multipartThreshold,
                                  self.__multipartPartSize,
                                  self.__multipartThreadsNum)
        uploader.setClientId(self.__accessKeyId)
        res = uploader.upload()

        uploadAddress = uploadInfo['UploadAddress']
        bucketHost = uploadAddress['Endpoint'].replace('://',
                                                       '://' + uploadAddress[
                                                           'Bucket'] + ".")
        logger.info(
            "UploadFile %s Finish, MediaId: %s, FilePath: %s, Destination: %s/%s" % (
                uploadInfo['MediaType'], uploadInfo['MediaId'], filePath,
                bucketHost, object))
        # pprint(vars(res.resp))
        return res

    # 使用上传凭证和地址信息初始化OSS客户端（注意需要先Base64解码并Json Decode再传入）
    # 如果上传的ECS位于点播相同的存储区域（如上海），则可以指定internal为True，通过内网上传更快且免费
    def __createOssClient(self, uploadAuth, uploadAddress):
        auth = oss2.StsAuth(uploadAuth['AccessKeyId'],
                            uploadAuth['AccessKeySecret'],
                            uploadAuth['SecurityToken'])
        endpoint = AliyunVodUtils.convertOssInternal(uploadAddress['Endpoint'],
                                                     self.__ecsRegion)
        self.__bucketClient = oss2.Bucket(auth, endpoint,
                                          uploadAddress['Bucket'],
                                          connect_timeout=self.__connTimeout,
                                          enable_crc=self.__EnableCrc)
        return self.__bucketClient

    def __refreshUploadAuth(self, videoId):
        uploadInfo = self.__refresh_upload_video(videoId)
        uploadAuth = uploadInfo['UploadAuth']
        uploadAddress = uploadInfo['UploadAddress']
        return self.__createOssClient(uploadAuth, uploadAddress)


from oss2 import SizedFileAdapter
from oss2.models import PartInfo
from aliyunsdkcore.utils import parameter_helper as helper


class _VodResumableUploader:
    def __init__(self, bucket, filePath, object, uploadInfo, headers,
                 progressCallback,
                 refreshAuthCallback):
        self.__bucket = bucket
        self.__filePath = filePath
        self.__object = object
        self.__uploadInfo = uploadInfo
        self.__totalSize = None
        self.__headers = headers
        self.__mtime = os.path.getmtime(filePath)
        self.__progressCallback = progressCallback
        self.__refreshAuthCallback = refreshAuthCallback

        self.__threshold = None
        self.__partSize = None
        self.__threadsNum = None
        self.__uploadId = 0

        self.__record = {}
        self.__finishedSize = 0
        self.__finishedParts = []
        self.__filePartHash = None
        self.__clientId = None

    def setMultipartInfo(self, threshold, partSize, threadsNum):
        self.__threshold = threshold
        self.__partSize = partSize
        self.__threadsNum = threadsNum

    def setClientId(self, clientId):
        self.__clientId = clientId

    def upload(self):
        self.__totalSize = os.path.getsize(self.__filePath)
        if self.__threshold and self.__totalSize <= self.__threshold:
            return self.simpleUpload()
        else:
            return self.multipartUpload()

    def simpleUpload(self):
        with open(AliyunVodUtils.toUnicode(self.__filePath), 'rb') as f:
            result = self.__bucket.put_object(self.__object, f,
                                              headers=self.__headers,
                                              progress_callback=None)
            if self.__uploadInfo['MediaType'] == 'videos':
                self.__reportUploadProgress('put', 1, self.__totalSize)

            return result

    def multipartUpload(self):
        psize = oss2.determine_part_size(self.__totalSize,
                                         preferred_size=self.__partSize)

        # 初始化分片
        self.__uploadId = self.__bucket.init_multipart_upload(
            self.__object).upload_id

        startTime = time.time()
        expireSeconds = 2500  # 上传凭证有效期3000秒，提前刷新
        # 逐个上传分片
        with open(AliyunVodUtils.toUnicode(self.__filePath), 'rb') as fileObj:
            partNumber = 1
            offset = 0

            while offset < self.__totalSize:
                uploadSize = min(psize, self.__totalSize - offset)
                # logger.info("UploadPart, FilePath: %s, VideoId: %s, UploadId: %s, PartNumber: %s, PartSize: %s" % (self.__fileName, self.__videoId, self.__uploadId, partNumber, uploadSize))
                result = self.__bucket.upload_part(self.__object,
                                                   self.__uploadId, partNumber,
                                                   SizedFileAdapter(fileObj,
                                                                    uploadSize))
                # print(result.request_id)
                self.__finishedParts.append(PartInfo(partNumber, result.etag))
                offset += uploadSize
                partNumber += 1

                # 上传进度回调
                self.__progressCallback(offset, self.__totalSize)

                if self.__uploadInfo['MediaType'] == 'videos':
                    # 上报上传进度
                    self.__reportUploadProgress('multipart', partNumber - 1,
                                                offset)

                    # 检测上传凭证是否过期
                    nowTime = time.time()
                    if nowTime - startTime >= expireSeconds:
                        self.__bucket = self.__refreshAuthCallback(
                            self.__uploadInfo['MediaId'])
                        startTime = nowTime

        # 完成分片上传
        self.__bucket.complete_multipart_upload(self.__object, self.__uploadId,
                                                self.__finishedParts,
                                                headers=self.__headers)

        return result

    def __reportUploadProgress(self, uploadMethod, donePartsCount, doneBytes):
        reportHost = 'vod.cn-shanghai.aliyuncs.com'
        sdkVersion = '1.3.1'
        reportKey = 'HBL9nnSwhtU2$STX'

        uploadPoint = {'upMethod': uploadMethod, 'partSize': self.__partSize,
                       'doneBytes': doneBytes}
        timestamp = int(time.time())
        authInfo = AliyunVodUtils.getStringMd5(
            "%s|%s|%s" % (self.__clientId, reportKey, timestamp))

        fields = {'Action': 'ReportUploadProgress', 'Format': 'JSON',
                  'Version': '2017-03-21',
                  'Timestamp': helper.get_iso_8061_date(),
                  'SignatureNonce': helper.get_uuid(),
                  'VideoId': self.__uploadInfo['MediaId'],
                  'Source': 'PythonSDK',
                  'ClientId': self.__clientId,
                  'BusinessType': 'UploadVideo', 'TerminalType': 'PC',
                  'DeviceModel': 'Server',
                  'AppVersion': sdkVersion, 'AuthTimestamp': timestamp,
                  'AuthInfo': authInfo,

                  'FileName': self.__filePath,
                  'FileHash': self.__getFilePartHash(self.__clientId,
                                                     self.__filePath,
                                                     self.__totalSize),
                  'FileSize': self.__totalSize, 'FileCreateTime': timestamp,
                  'UploadRatio': 0,
                  'UploadId': self.__uploadId,
                  'DonePartsCount': donePartsCount, 'PartSize': self.__partSize,
                  'UploadPoint': json.dumps(uploadPoint),
                  'UploadAddress': self.__uploadInfo['OriUploadAddress']
                  }
        requests.post('http://' + reportHost, fields, timeout=1)

    def __getFilePartHash(self, clientId, filePath, fileSize):
        if self.__filePartHash:
            return self.__filePartHash

        length = 1 * 1024 * 1024
        if fileSize < length:
            length = fileSize

        try:
            fp = open(AliyunVodUtils.toUnicode(filePath), 'rb')
            strVal = fp.read(length)
            self.__filePartHash = AliyunVodUtils.getStringMd5(strVal, False)
            fp.close()
        except:
            self.__filePartHash = "%s|%s|%s" % (
            clientId, filePath, self.__mtime)

        return self.__filePartHash
