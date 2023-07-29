import configparser
import json
import os
import uuid
from datetime import timedelta, datetime
import sys
import random
import requests
import schedule
import openai
from time import sleep
import logging
from time import time

from scraper import RssScrap


DEBUG = False

logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("in.log"),
        logging.StreamHandler()
    ]
)


def ask_chatgpt(config, content, token_limit=150):
    preamble = config["gpt_preamble"]
    bio = config["bio"]

    system_messages = [
        {"role": "system", "content": preamble},
        {"role": "system", "content": bio},
    ]

    user_messages = [
        {"role": "user", "content": item.get('description')} for item in content
    ]

    gpt_messages = system_messages + user_messages

    request_wait_time_seconds = 1
    response_text = ''
    while True:
        try:
            if DEBUG:
                logging.info(f"[!!] DEBUG: {gpt_messages}")
                return "This is a test message"

            logging.info(f"Requesting GPT with messages: {gpt_messages}")
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=gpt_messages,
                max_tokens=token_limit,
                stop=["xx"],
            )
            logging.info(f'Usage: {response.get("usage")}')
            response_text = response.choices[0].message['content'].strip()
            logging.info(f"Text from GPT: {response_text}")
            return response_text
        except openai.error.RateLimitError:
            logging.error(f"Rate limit exceeded. Retrying in {request_wait_time_seconds} seconds...")
        except openai.error.ServiceUnavailableError:
            logging.error("The server is overloaded or not ready yet.  Retrying in 60 seconds...")
        except Exception as e:
            logging.error(f"Error: {e}")
        finally:
            with open("out.log", "a") as f:
                f.write(f"{datetime.now()}: {response_text}\n")
            request_wait_time_seconds *= 2
            logging.info(f"Request wait time: {request_wait_time_seconds}")
            sleep(request_wait_time_seconds)


def get_session():
    if "linkedin_session" not in globals():
        session = requests.Session()
        globals()["linkedin_session"] = session
    return globals()["linkedin_session"]


def post_pool(payload_text, cookies_conf):
    cookie_value = "li_at=%s; JSESSIONID=\"%s\"" % (cookies_conf["li_at"], cookies_conf["JSESSIONID"])
    headers = {
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json; charset=UTF-8",
        "csrf-token": cookies_conf["JSESSIONID"],
        "referrer-policy": "strict-origin-when-cross-origin, strict-origin-when-cross-origin",
        "origin": "https://www.linkedin.com",
        "Referrer": "https://www.linkedin.com/feed/",
        "Referrer-Policy": "strict-origin-when-cross-origin, strict-origin-when-cross-origin",
        "cookie": cookie_value
    }
    json_pool = {
        'question': 'enquete teste 2',
        'duration': 259200,  # 3 days
        'options': [
            'asd2',
            'asd2',
            'asd2',
        ],
    }
    json_post = {
      "visibleToConnectionsOnly": True,
      "externalAudienceProviders": [],
      "commentaryV2": {
        "text": "enquete asd asd asd asdasd",
        "attributes": []
      },
      "origin": "FEED",
      "allowedCommentersScope": "CONNECTIONS_ONLY",
      "postState": "PUBLISHED",
      "media": [
        {
          "mediaUrn": "urn:li:fs_poll:7091150921715396608"
        }
      ]
    }
    try:
        get_urn = requests.post(
            'https://www.linkedin.com/voyager/api/voyagerFeedPollsPoll',
            headers=headers,
            json=json_pool,
            verify=False,
        )
        get_urn.raise_for_status()

        urn = get_urn.headers['Location'].split('/')[-1]
        json_post['media'][0]['mediaUrn'] = urn
        json_post['media'][0]['poll']['question'] = json_pool['question']
        json_post['media'][0]['poll']['options'] = json_pool['options']

        response_post = requests.post(
            'https://www.linkedin.com/voyager/api/contentcreation/normShares',
            headers=headers,
            json=json_post,
            verify=False,
        )
        response_post.raise_for_status()

        logging.info(f"LinkedIn queue success!")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error posting to LinkedIn: {e}")


def post_with_image(post_info, cookies_conf):
    cookie_value = "li_at=%s; JSESSIONID=\"%s\"" % (cookies_conf["li_at"], cookies_conf["JSESSIONID"])
    headers = {
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json; charset=UTF-8",
        "Csrf-Token": cookies_conf["JSESSIONID"],
        "referrer-policy": "strict-origin-when-cross-origin, strict-origin-when-cross-origin",
        "origin": "https://www.linkedin.com",
        "Referrer": "https://www.linkedin.com/feed/",
        "Referrer-Policy": "strict-origin-when-cross-origin, strict-origin-when-cross-origin",
        "cookie": cookie_value
    }
    cookie = {
        "li_at": cookies_conf["li_at"],
        "JSESSIONID": cookies_conf["JSESSIONID"]
    }
    image = post_info["image"]
    image_bin = requests.get(image).content
    image_size = len(image_bin)
    payload = {
      "mediaUploadType": "IMAGE_SHARING",
      "fileSize": image_size,
      "filename": f"{str(uuid.uuid4()).replace('-', '')}.png"
    }
    image_response = requests.post(
        'https://www.linkedin.com/voyager/api/voyagerVideoDashMediaUploadMetadata?action=upload',
        headers=headers,
        json=json.dumps(payload),
        cookies=cookie,
    )
    image_response.raise_for_status()
    logging.info(f"LinkedIn image get info success!")
    upload_response = image_response.json()
    upload_url = upload_response['data']['value']['singleUploadUrl']
    media_urn = upload_response['data']['value']['urn']
    upload_put = requests.put(
        upload_url,
        headers=headers,
        data=image_bin,
        verify=False,
    )
    upload_put.raise_for_status()
    logging.info(f"LinkedIn image upload success!")
    post_payload = {
      "visibleToConnectionsOnly": False,
      "externalAudienceProviders": [],
      "commentaryV2": {
        "text": post_info["text"],
        "attributes": []
      },
      "origin": "FEED",
      "allowedCommentersScope": "CONNECTIONS_ONLY",
      "postState": "PUBLISHED",
      "media": [
        {
          "category": "IMAGE",
          "mediaUrn": media_urn,
          "tapTargets": []
        }
      ]
    }
    response_post = requests.post(
        'https://www.linkedin.com/voyager/api/contentcreation/normShares',
        headers=headers,
        json=json.dumps(post_payload),
        verify=False,
    )
    response_post.raise_for_status()
    logging.info(f"LinkedIn post with image success!")


def post_linkedin(payload_text, cookies_conf):
    payload = {
        "visibleToConnectionsOnly": False,
        "externalAudienceProviders": [],
        "commentaryV2": {
            "text": payload_text,
            "attributes": []
        },
        "origin": "FEED",
        "allowedCommentersScope": "ALL",
        "postState": "PUBLISHED",
        "media": []
    }
    payload = json.dumps(payload)
    cookie_value = "li_at=%s; JSESSIONID=\"%s\"" % (cookies_conf["li_at"], cookies_conf["JSESSIONID"])
    headers = {
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json; charset=UTF-8",
        "csrf-token": cookies_conf["JSESSIONID"],
        "referrer-policy": "strict-origin-when-cross-origin, strict-origin-when-cross-origin",
        "origin": "https://www.linkedin.com",
        "Referrer": "https://www.linkedin.com/feed/",
        "Referrer-Policy": "strict-origin-when-cross-origin, strict-origin-when-cross-origin",
        "cookie": cookie_value
    }

    post_endpoint = "https://www.linkedin.com/voyager/api/contentcreation/normShares"

    try:
        response = requests.post(post_endpoint, headers=headers, data=payload)
        response.raise_for_status()
        logging.info(f"LinkedIn post success")
        if response.json().get('someKey', None) == 'expectedValue':
            pass

    except requests.exceptions.RequestException as e:
        logging.error(f"Error posting to LinkedIn: {e}")


def main(config_path='config.ini'):
    config = configparser.ConfigParser()
    config.read(config_path)

    settings = config['settings']
    gpt_token_limit = int(settings['gpt_token_limit'])
    scrape_char_limit = int(settings['scrape_char_limit'])
    openai.api_key = settings['open_ai_api_key']

    cookies_conf = config['cookies']

    urls = config['websites']['websites'].split()

    content = []
    for url in urls:
        data = RssScrap(url, scrape_char_limit).fetch_content()
        if data:
            content.append(data)
    random.shuffle(content)

    gpt_res = ask_chatgpt(settings, content, token_limit=gpt_token_limit)
    post_linkedin(gpt_res, cookies_conf)
    # content = content[0]
    # content['text'] = gpt_res
    # post_with_image(content, cookies_conf)


def main_task(**kwargs):
    main(**kwargs)
    schedule_next_task()
    logging.info("Task completed")


def schedule_next_task(**kwargs):
    schedule.clear()
    logging.info("Scheduling next task")
    minutes_for_next_task = random.randint(30, 90)
    time_to_execute = datetime.now() + timedelta(minutes=minutes_for_next_task)
    logging.info(f"Next task scheduled in {minutes_for_next_task} minutes. Time to execute: {time_to_execute}")
    schedule.every(minutes_for_next_task).minutes.do(main_task, **kwargs)


if __name__ == "__main__":

    main()

    config_file_path = None
    if len(sys.argv) > 1:
        config_file_path = sys.argv[1]
        schedule_next_task(config_path=config_file_path)
    else:
        schedule_next_task()

    while True:
        schedule.run_pending()
        sleep(1)
