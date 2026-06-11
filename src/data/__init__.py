"""
数据获取层初始化
修复 Windows 中文用户名路径导致的 SSL 证书问题
"""
import os
import shutil
import certifi


def _fix_ssl_cert():
    """将 SSL 证书复制到纯 ASCII 路径，避免 curl_cffi 读取含中文路径时失败"""
    try:
        # 如果环境变量已经设置了有效的路径，跳过
        for key in ["SSL_CERT_FILE", "CURL_CA_BUNDLE"]:
            existing = os.environ.get(key, "")
            if existing and os.path.exists(existing) and existing.isascii():
                return True

        ascii_paths = ["C:/Windows/Temp/cacert.pem", "C:/temp/cacert.pem"]
        for p in ascii_paths:
            try:
                d = os.path.dirname(p)
                if d and not os.path.exists(d):
                    os.makedirs(d, exist_ok=True)
                shutil.copy2(certifi.where(), p)
                os.environ["SSL_CERT_FILE"] = p
                os.environ["CURL_CA_BUNDLE"] = p
                os.environ["REQUESTS_CA_BUNDLE"] = p
                return True
            except Exception:
                continue
    except Exception:
        pass
    return False


try:
    _fix_ssl_cert()
except Exception:
    pass
