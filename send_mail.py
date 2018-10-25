#!/usr/bin/env python
# coding: utf-8

"""
    function: 发送带有嵌入式图像和纯文本消息的HTML电子邮件
"""

import os
import time
import smtplib
import configparser

from glob import glob
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.header import Header
from jinja2 import Environment, FileSystemLoader


def _drawing_to_html(ips_info, domains_info, template_path, template_file):
    """ 渲染数据，返回渲染数据之后的html

    :param ips_info: 需要渲染的ip数据
    :param domains_info: 需要渲染的域名数据
    :param template_path: 模板路径
    :param template_file: 模板文件名
    :return: 渲染数据之后的模板
    """

    # 设置要渲染的数据及其格式
    event_data = {
        "event": {
            "alert_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "description": "",
            "now": datetime.now().strftime('%Y'),
        },
        "event_detail": {
            "ips_info": [],
            "domains_info": [],
        }
    }

    event_data["event_detail"]["ips_info"] = ips_info
    event_data["event_detail"]["domains_info"] = domains_info

    try:
        # 配置模板文件的搜索路径
        template_loader = FileSystemLoader(searchpath=template_path)
        # 创建环境变量
        env = Environment(loader=template_loader)

        # 加载模板，渲染数据
        template = env.get_template(template_file)
        html = template.render(**event_data)
    except Exception as e:
        raise e

    return html


def send_mail(receivers, cc, ips_info, domains_info):
    """ 发送邮件

    :param receivers: type of list，收件人邮箱列表
    :param cc: type of list，抄送人邮箱列表
    :param ips_info: type of json，需要渲染的ip数据信息
    :param domains_info: type of json，需要渲染的domain数据信息
    :return: 发送邮件结果，附带消息
    """

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    email_file = os.path.join(base_dir, 'server_email', 'email.conf')
    config = configparser.ConfigParser()
    try:
        config.read(email_file, encoding="utf-8")
        sender = config.get("SERVER_EMAIL", "SENDER")
        stmp_server = config.get("SERVER_EMAIL", "SMTP_SERVER")
        user_name = config.get("SERVER_EMAIL", "USER_NAME")
        password = config.get("SERVER_EMAIL", "PASSWORD")
        port = config.get("SERVER_EMAIL", "PORT")
        authentication = config.get("SERVER_EMAIL", "AUTHENTICATION")
        ssl = config.get("SERVER_EMAIL", "SSL")
        template_html_path = config.get("FILE_PATH", "TEMPLATE_HTML_PATH")
        template_html_path = os.path.join(base_dir, template_html_path)
        template_file = config.get("FILE_PATH", "TEMPLATE_FILE")
        template_images_path = config.get("FILE_PATH", "TEMPLATE_IMAGES_PATH")
        template_images_path = os.path.join(base_dir, template_html_path, template_images_path)
        header = config.get("EMAIL_INFO", "HEADER")
    except Exception as e:
        return False, str(e)

    msg_root = MIMEMultipart()
    msg_root['subject'] = Header(header, 'utf-8')
    msg_root['from'] = sender
    msg_root['to'] = ",".join(receivers)
    msg_root['cc'] = ",".join(cc)
    msg_root['date'] = time.strftime("%a,%d %b %Y %H:%M:%S %z")

    try:
        html = _drawing_to_html(ips_info, domains_info, template_html_path, template_file)
    except Exception as e:
        return False, str(e)

    msg_text = MIMEText(html, 'html', 'utf-8')
    msg_root.attach(msg_text)

    try:
        _attach_image(msg_root, template_images_path)
        if ssl == 'false':
            smtp = smtplib.SMTP(host=stmp_server, port=int(port), timeout=300)
        else:
            smtp = smtplib.SMTP_SSL(host=stmp_server, port=int(port), timeout=300)

        if authentication == 'true':
            smtp.ehlo()
            smtp.login(user_name, password)

        smtp.sendmail(sender, receivers+cc, msg_root.as_string())
        smtp.quit()
    except Exception as e:
        return False, str(e)

    message = 'Send email success'
    return True, message


def _attach_image(msg_root, template_images_path):
    """ 向html邮件体中填充图片

    :param msg_root: type of dict
    :param template_images_path: images path
    :return: None
    """

    source_image_info = _get_source_image_info(template_images_path)

    for image_name, image_path in source_image_info.items():
        try:
            msg_image = MIMEImage(open(image_path, 'rb').read())
            msg_image.add_header('Content-ID', image_name)
            msg_root.attach(msg_image)
        except Exception as e:
            raise e


def _get_source_image_info(template_images_path):
    """ 获取填充图片每个图片名称及其路径

    :param images path
    :return: type of dict, image name->image path
    """

    source_image_info = {}
    source_images = glob(os.path.join(template_images_path, "*"))

    for source_image in source_images:
        _, file_name = os.path.split(source_image)
        if file_name:
            source_image_info[file_name] = source_image

    return source_image_info


if __name__ == "__main__":
    receivers = ['zhoubobo@nsfocus.com']
    cc = []
    ip_info = {
        'ip': '8.8.8.8',
        'monitor_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'threat_type': u'DDOS攻击'
    }

    domain_info = {
        'domain': 'www.baidu.com',
        'monitor_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'threat_type': u'挂马网站'
    }

    ips_info = []
    ips_info.append(ip_info)
    domains_info = []
    domains_info.append(domain_info)

    result, msg = send_mail(receivers, cc, ips_info, domains_info)
    print(result, msg)


