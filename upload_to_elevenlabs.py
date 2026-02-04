#!/usr/bin/env python3
import os
from pathlib import Path

try:
    from elevenlabs import ElevenLabs
except ImportError:
    import subprocess
    subprocess.run(['pip3', 'install', 'elevenlabs'], check=True)
    from elevenlabs import ElevenLabs

API_KEY = 'a3e299b01b146bc05f7de7606217516725298b2cb157d3a0964fc6963d5124ec'

AUDIO_DIR = Path('/Users/lunhsiangyuan/Projects/yuan-voice-clone')
AUDIO_FILES = [
    AUDIO_DIR / '袁倫祥醫師_新雲林之聲_攝護腺常見疾病.mp3',
    AUDIO_DIR / '袁倫祥醫師_新雲林之聲_1090703_攝護腺疾病.mp3',
    AUDIO_DIR / '袁倫祥醫師_台灣癌症基金會專訪_攝護腺癌大解惑.mp3',
]

def main():
    print('=' * 60)
    print('袁倫祥醫師 ElevenLabs 聲音模型上傳')
    print('=' * 60)
    
    existing_files = [f for f in AUDIO_FILES if f.exists()]
    print(f'找到 {len(existing_files)} 個音檔')
    
    client = ElevenLabs(api_key=API_KEY)
    
    # Check account
    try:
        user = client.user.get()
        print(f'帳戶等級: {user.subscription.tier}')
    except Exception as e:
        print(f'帳戶檢查: {e}')
    
    # Try IVC first (simpler)
    print('建立 Instant Voice Clone...')
    try:
        voice = client.voices.ivc.create(
            name='袁倫祥醫師',
            description='臺大醫院雲林分院泌尿部副主任',
            files=[str(f) for f in existing_files]
        )
        print(f'成功！Voice ID: {voice.voice_id}')
    except Exception as e:
        print(f'錯誤: {e}')

if __name__ == '__main__':
    main()
