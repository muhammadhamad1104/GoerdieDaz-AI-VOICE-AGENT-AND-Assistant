from pathlib import Path
from dotenv import load_dotenv
import os
import requests, json

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

url = 'https://api.elevenlabs.io/v1/voices'
headers = {'xi-api-key': os.environ["ELEVENLABS_API_KEY"]}
resp = requests.get(url, headers=headers)
voices = resp.json().get('voices', [])
for v in voices:
    labels = v.get('labels', {})
    vid = v['voice_id']
    name = v['name']
    accent = labels.get('accent', '?')
    age = labels.get('age', '?')
    gender = labels.get('gender', '?')
    desc = labels.get('description', labels.get('descriptive', '?'))
    print(f"{vid} | {name:25s} | accent={accent:15s} | age={age:12s} | gender={gender:8s} | desc={desc}")
