from __future__ import annotations
import json
import urllib.parse
import urllib.request

class CloudError(RuntimeError): pass

class CloudApi:
    def __init__(self, url: str, timeout: int = 12):
        self.url=url.strip(); self.timeout=timeout

    def _decode(self, raw: bytes):
        try: data=json.loads(raw.decode('utf-8'))
        except Exception as e: raise CloudError(f'Invalid JSON: {e}')
        if isinstance(data,dict) and (data.get('ok') is False or data.get('success') is False or data.get('status')=='error'):
            raise CloudError(str(data.get('message') or data.get('error') or 'Cloud request failed'))
        return data

    def get(self, action: str, **params):
        q={'action':action, **{k:str(v) for k,v in params.items() if v is not None}}
        url=self.url + ('&' if '?' in self.url else '?') + urllib.parse.urlencode(q)
        req=urllib.request.Request(url,headers={'User-Agent':'MizanCode-Desktop/6.1','Accept':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r: return self._decode(r.read())
        except Exception as e: raise CloudError(str(e))

    def post(self, action: str, payload: dict):
        body={'action':action, **payload}
        raw=json.dumps(body,ensure_ascii=False).encode('utf-8')
        req=urllib.request.Request(self.url,data=raw,headers={'User-Agent':'MizanCode-Desktop/6.1','Content-Type':'application/json; charset=utf-8','Accept':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r: return self._decode(r.read())
        except Exception as post_err:
            try:
                encoded={k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in body.items()}
                data=urllib.parse.urlencode(encoded).encode('utf-8')
                req2=urllib.request.Request(self.url,data=data,headers={'User-Agent':'MizanCode-Desktop/6.1','Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'},method='POST')
                with urllib.request.urlopen(req2,timeout=self.timeout) as r: return self._decode(r.read())
            except Exception as e: raise CloudError(f'{post_err}; fallback: {e}')
