"""Check existing Git Credential Manager access; never print a credential."""
import json
import os
import subprocess
import urllib.request

def credentials():
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never'}
    result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                            text=True, capture_output=True, env=env, timeout=25)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if not values.get('password'):
        raise RuntimeError('GitHub sign-in is needed; no saved GitHub credential was available.')
    return values['password']

def api(path, token, data=None):
    request = urllib.request.Request('https://api.github.com'+path,
        headers={'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json', 'User-Agent': 'WakeyMonster'},
        data=json.dumps(data).encode() if data is not None else None)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

if __name__ == '__main__':
    try:
        account = api('/user', credentials())
        print('GitHub account:', account['login'])
    except Exception as exc:
        print('GitHub access unavailable:', str(exc))
        raise SystemExit(1)
