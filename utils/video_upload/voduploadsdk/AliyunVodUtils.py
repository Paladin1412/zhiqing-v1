# -*- coding: UTF-8 -*-
import os,sys
import hashlib
import datetime
import functools
import logging
from oss2.exceptions import OssError
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkcore.acs_exception.exceptions import ClientException
import traceback
import requests

if sys.version_info[0] == 3:
    import urllib.parse
else:
    from urllib import unquote


VOD_PRINT_INFO_LOG_SWITCH = 1

class AliyunVodLog:
    """
    VOD日志类，基于logging实现
    """
    @staticmethod
    def printLogStr(msg, *args, **kwargs):
        if VOD_PRINT_INFO_LOG_SWITCH:
            print("[%s]%s" % (AliyunVodUtils.getCurrentTimeStr(), msg))
        
    @staticmethod
    def info(msg, *args, **kwargs):
        logging.info(msg, *args, **kwargs)
        AliyunVodLog.printLogStr(msg, *args, **kwargs)
    
    @staticmethod
    def error(msg, *args, **kwargs):
        logging.error(msg, *args, **kwargs)
        AliyunVodLog.printLogStr(msg, *args, **kwargs)
    
    @staticmethod
    def warning(msg, *args, **kwargs):
        logging.warning(msg, *args, **kwargs)
        AliyunVodLog.printLogStr(msg, *args, **kwargs)
        
logger = AliyunVodLog
        
        
class AliyunVodUtils:
    """
    VOD上传SDK的工具类，提供截取字符串、获取扩展名、获取文件名等静态函数
    """

    # 截取字符串，在不超过最大字节数前提下确保中文字符不被截断出现乱码（先转换成unicode，再取子串，然后转换成utf-8）
    @staticmethod
    def subString(strVal, maxBytes, charSet='utf-8'):
        i = maxBytes
        if sys.version_info[0] == 3:
            while len(strVal.encode(charSet)) > maxBytes:
                if i < 0:
                    return ''
                strVal = strVal[:i]
                i -= 1
        else:
            while len(strVal) > maxBytes:
                if i < 0:
                    return ''
                strVal = strVal.decode(charSet)[:i].encode(charSet)
                i -= 1
        return strVal
    
    @staticmethod
    def getFileExtension(fileName):
        end = fileName.rfind('?')
        if end <= 0:
            end = len(fileName)

        i = fileName.rfind('.')
        if i >= 0:
            return fileName[i+1:end].lower()
        else:
            return None

    # urldecode
    @staticmethod
    def urlDecode(fileUrl):
        if sys.version_info[0] == 3:
            return urllib.parse.unquote(fileUrl)
        else:
            return unquote(fileUrl)

    # urlencode
    @staticmethod
    def urlEncode(fileUrl):
        if sys.version_info[0] == 3:
            return urllib.parse.urlencode(fileUrl)
        else:
            return urllib.urlencode(fileUrl)

    # 获取Url的摘要地址（去除?后的参数，如果有）以及文件名
    @staticmethod   
    def getFileBriefPath(fileUrl):
        #fileUrl = AliyunVodUtils.urlDecode(fileUrl)
        i = fileUrl.rfind('?')
        if i > 0:
            briefPath = fileUrl[:i]
        else:
            briefPath = fileUrl

        briefName = os.path.basename(briefPath)
        return briefPath, AliyunVodUtils.urlDecode(briefName)
    
    @staticmethod
    def getStringMd5(strVal, isEncode=True):
        m = hashlib.md5()
        m.update(strVal.encode('utf-8') if isEncode else strVal)
        return m.hexdigest()
    
    @staticmethod
    def getCurrentTimeStr():
        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 将oss地址转换为内网地址（如果脚本部署的ecs与oss bucket在同一区域）
    @staticmethod
    def convertOssInternal(ossUrl, ecsRegion=None, isVpc=False):
        if (not ossUrl) or (not ecsRegion):
            return ossUrl
        
        availableRegions = ['cn-qingdao', 'cn-beijing', 'cn-zhangjiakou', 'cn-huhehaote', 'cn-hangzhou', 'cn-shanghai', 'cn-shenzhen',
                               'cn-hongkong', 'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3', 
                               'ap-northeast-1', 'us-west-1', 'us-east-1', 'eu-central-1', 'me-east-1']
        if ecsRegion not in availableRegions:
            return ossUrl

        ossUrl = ossUrl.replace("https:", "http:")
        if isVpc:
            return ossUrl.replace("oss-%s.aliyuncs.com" % (ecsRegion), "vpc100-oss-%s.aliyuncs.com" % (ecsRegion))
        else:
            return ossUrl.replace("oss-%s.aliyuncs.com" % (ecsRegion), "oss-%s-internal.aliyuncs.com" % (ecsRegion))

    # 把输入转换为unicode
    @staticmethod
    def toUnicode(data):
        if isinstance(data, bytes):
            return data.decode('utf-8')
        else:
            return data

    # 替换路径中的文件名；考虑分隔符为"/" 或 "\"(windows)
    @staticmethod
    def replaceFileName(filePath, replace):
        if len(filePath) <= 0 or len(replace) <= 0:
            return filePath

        filePath = AliyunVodUtils.urlDecode(filePath)
        separator = '/'
        start = filePath.rfind(separator)
        if start < 0:
            separator = '\\'
            start = filePath.rfind(separator)
            if start < 0:
                return None

        result = "%s%s%s" % (filePath[0:start], separator, replace)
        return result

    # 创建文件中的目录
    @staticmethod
    def mkDir(filePath):
        if len(filePath) <= 0:
            return -1

        separator = '/'
        i = filePath.rfind(separator)
        if i < 0:
            separator = '\\'
            i = filePath.rfind(separator)
            if i < 0:
                return -2

        dirs = filePath[:i]
        if os.path.exists(dirs) and os.path.isdir(dirs):
            return 0

        os.makedirs(dirs)
        return 1



class AliyunVodException(Exception):
    """
    VOD上传SDK的异常类，做统一的异常处理，外部捕获此异常即可
    """
    
    def __init__(self, type, code, msg, http_status=None, request_id=None):
        Exception.__init__(self)
        self.type = type or 'UnkownError'
        self.code = code
        self.message = msg
        self.http_status = http_status or 'NULL'
        self.request_id = request_id or 'NULL'
    
    def __str__(self):
        return "Type: %s, Code: %s, Message: %s, HTTPStatus: %s, RequestId: %s" % (
            self.type, self.code, self.message, str(self.http_status), self.request_id)
        
def catch_error(method):
    """
    装饰器，将内部异常转换成统一的异常类AliyunVodException
    """
    
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except ServerException as e:
            # 可能原因：AK错误、账号无权限、参数错误等
            raise AliyunVodException('ServerException', e.get_error_code(), e.get_error_msg(), e.get_http_status(), e.get_request_id())
            logger.error("ServerException: %s", e)
        except ClientException as e:
            # 可能原因：本地网络故障（如不能连接外网）等
            raise AliyunVodException('ClientException', e.get_error_code(), e.get_error_msg())
            logger.error("ClientException: %s", e)
        except OssError as e:
            # 可能原因：上传凭证过期等
            raise AliyunVodException('OssError', e.code, e.message, e.status, e.request_id)
            logger.error("OssError: %s", e)
        except IOError as e:
            # 可能原因：文件URL不能访问、本地文件无法读取等
            raise AliyunVodException('IOError', repr(e), traceback.format_exc())
            logger.error("IOError: %s", traceback.format_exc())
        except OSError as e:
            # 可能原因：本地文件不存在等
            raise AliyunVodException('OSError', repr(e), traceback.format_exc())
            logger.error("OSError: %s", traceback.format_exc())
        except AliyunVodException as e:
            # 可能原因：参数错误
            raise e
            logger.error("VodException: %s", e)
        except Exception as e:
            raise AliyunVodException('UnkownException', repr(e), traceback.format_exc())
            logger.error("UnkownException: %s", traceback.format_exc())
        except:
            raise AliyunVodException('UnkownError', 'UnkownError', traceback.format_exc())
            logger.error("UnkownError: %s", traceback.format_exc())
            
    return wrapper


class AliyunVodDownloader:
    """
        VOD网络文件的下载类，上传网络文件时会先下载到本地临时目录，再上传到点播
    """

    def __init__(self, localDir=None):
        if localDir:
            self.__localDir = localDir
        else:
            p = os.path.dirname(os.path.realpath(__file__))
            self.__localDir = os.path.dirname(p) + '/dlfiles'

    def setSaveLocalDir(self, localDir):
        self.__localDir = localDir

    def getSaveLocalDir(self):
        return self.__localDir

    def downloadFile(self, fileUrl, localFileName, fileSize=None):
        localPath = self.__localDir + '/' + localFileName
        logger.info("Download %s To %s" % (fileUrl, localPath))
        try:
            lsize = self.getFileSize(localPath)
            if fileSize and lsize == fileSize:
                logger.info('Download OK, File Exists')
                return 0, localPath

            AliyunVodUtils.mkDir(self.__localDir)

            err, webPage = self.__openWebFile(fileUrl, lsize)
            if err == 0:
                logger.info('Download OK, File Exists')
                webPage.close()
                return 0, localPath

            fileObj = open(localPath, 'ab+')
            for chunk in webPage.iter_content(chunk_size=8 * 1024):
                if chunk:
                    fileObj.write(chunk)
        except Exception as e:
            logger.error("Download fail: %s" % (e))
            return -1, None

        fileObj.close()
        webPage.close()
        logger.info('Download OK')
        return 1, localPath

    def getFileSize(self, filePath):
        try:
            lsize = os.stat(filePath).st_size
        except:
            lsize = 0

        return lsize


    def __openWebFile(self, fileUrl, offset):
        webPage = None
        try:
            headers = {'Range': 'bytes=%d-' % offset}
            webPage = requests.get(fileUrl, stream=True, headers=headers, timeout=120, verify=False)
            status_code = webPage.status_code
            err = -1
            if status_code in [200, 206]:
                err = 1
            elif status_code == 416:
                err = 0
            else:
                logger.error("Download offset %s fail, invalid url, status: %s" % (offset, status_code))
        except Exception as e:
            logger.error("Download offset %s fail: %s" % (offset, e))
            err = -2
        finally:
            return err, webPage

