import time, json, os

import requests
from requests_oauthlib import OAuth1

# Poll posting hack taken from https://gist.github.com/airhadoken/8742d16a2a190a3505a2

# using Twitter for Mac consumer API key
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
twitter_name = os.getenv("TWITTER_NAME")

base_url = "https://api.twitter.com/1.1/"
card_url = "https://caps.twitter.com/v2/cards/create"
upload_url = "https://upload.twitter.com/1.1/media/upload.json"

auth = OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

def request(method, url, params=None, headers=None, files=None):
	res = None
	trys = 3

	while trys > 0:
		try:
			if method == "POST":
				res = requests.post(url, auth=auth, params=params, headers=headers, files=files)
			elif method == "GET":
				res = requests.get(url, auth=auth, params=params, headers=headers, files=files)
			res.raise_for_status()
			break
		except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
			print("Requests Error", err)
			print("Sleeping and trying again")
			time.sleep(3)
		trys = trys - 1

	if not res:
		print("Request Error requesting url: ", url, res.status_code, end="")
		print(res.text)
		return False
	return res

def post_tweet(text, entries=None, duration=20, reply_id=None, reply_name=twitter_name, media_id=None):
	card_uri = None

	if entries:
		header = {
			"Accept": "*/*",
			"User-Agent": "Twitter-Mac/8.16 iOS/13.4 (Apple;MacBookAir6,1;;;;;1;2020)",
		}

		params = {
			"twitter:api:api:endpoint": "1",
			"twitter:card": "poll" + str(len(entries)) + "choice_text_only",
			"twitter:long:duration_minutes": duration
		}

		for i in range(len(entries)):
			params["twitter:string:choice" + str(i + 1) + "_label"] = entries[i]

		res = request("POST", card_url, params={"card_data": json.dumps(params)}, headers=header)
		card_uri = res.json()["card_uri"]

	params = {"status": text}

	if card_uri:
		params["card_uri"] = card_uri
		params["include_cards"] = 1
		params["card_platform"] = "iPhone-13"
		params["contributor_details"] = 1

	if reply_id:
		params["in_reply_to_status_id"] = int(reply_id)
		params["status"] = "@{} ".format(reply_name) + params["status"]

	if media_id:
		params["media_ids"] = [int(media_id)]

	res = request("POST", base_url + "statuses/update.json", params=params)
	return res.json()["id_str"]

def get_tweet(tweet_id):
	params = {
		"id": tweet_id,
		"cards_platform": "iPhone-13",
		"include_cards": 1,
	}

	res = request("GET", base_url + "statuses/show.json", params=params)
	return res.json()

def upload_image(img_path):
	files = {"media": open(img_path, "rb")}
	res = request("POST", upload_url, files=files)
	return res.json()["media_id_string"]

def delete_tweet(tweet_id):
	url = base_url + "statuses/destroy/" + str(tweet_id) + ".json"
	res = request("POST", url)
	return res.json()
