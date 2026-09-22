#VERSION: 2.10
# AUTHORS: Daniel Naranjo (garcianaranjodaniel@gmail.com)
# LICENSING INFORMATION

from novaprinter import prettyPrinter
import re
import json
import hashlib
import time
import sys
import tempfile
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar


class AnubisSolver:
    def solve(self, challenge_data):
        method = challenge_data.get('method', 'fast')
        difficulty = challenge_data.get('difficulty', 5)
        random_data = challenge_data.get('randomData', '')

        if method == 'metarefresh':
            elapsed = difficulty * 0.8
            time.sleep(elapsed)
            return {'response': random_data, 'nonce': 0, 'elapsedTime': elapsed}
        elif method == 'preact':
            start = time.time()
            time.sleep(difficulty * 0.08)
            response = hashlib.sha256(random_data.encode()).hexdigest()
            return {'response': response, 'nonce': 0, 'elapsedTime': time.time() - start}
        else:
            target_zeros = difficulty
            nonce = 0
            start = time.time()
            while True:
                hash_input = (random_data + str(nonce)).encode()
                hash_hex = hashlib.sha256(hash_input).hexdigest()
                if hash_hex.startswith('0' * target_zeros):
                    return {'response': hash_hex, 'nonce': nonce, 'elapsedTime': time.time() - start}
                nonce += 1


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class dontorrent(object):
    url = 'https://dontorrent.moi'
    name = 'DonTorrent'
    supported_categories = {
        'all': '',
    }

    FALLBACK_DOMAINS = [
        'https://dontorrent.moi',
        'https://dontorrent.supply',
        'https://dontorrent.soccer',
        'https://dontorrent.management',
        'https://dontorrent.review',
        'https://dontorrent.support',
        'https://dontorrent.science',
        'https://dontorrent.rocks',
    ]

    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        handler = urllib.request.HTTPCookieProcessor(self.cj)
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

        opener = urllib.request.build_opener(handler)
        opener.addheaders = [('User-Agent', self.user_agent)]
        self.opener = opener

        self.no_redirect_opener = urllib.request.build_opener(_NoRedirect(), handler)
        self.valid_domain = None
        self.anubis_solver = AnubisSolver()

    def _is_dt_domain(self, domain):
        if not domain.startswith('http'):
            domain = 'https://' + domain
        try:
            req = urllib.request.Request(domain, headers={'User-Agent': self.user_agent})
            response = self.no_redirect_opener.open(req, timeout=10)
            content = response.read().decode('utf-8', errors='ignore')
        except Exception:
            return False
        return 'anubis_challenge' in content or 'DonTorrent' in content or 'pelicula' in content.lower()

    def _telegram_domains(self):
        domains = []
        try:
            req = urllib.request.Request('https://t.me/s/DonTorrent', headers={'User-Agent': self.user_agent})
            html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
            texts = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.S)
            for text in texts:
                match = re.search(r'(?i)\b(dontorrent\.[a-z0-9]{2,12})\b', text)
                if match and match.group(1).lower() not in domains:
                    domains.append(match.group(1).lower())
            domains.reverse()
            for match in re.finditer(r'(?i)\b(dontorrent\.[a-z0-9]{2,12})\b', html):
                domain = match.group(1).lower()
                if domain not in domains:
                    domains.append(domain)
        except Exception:
            pass
        return domains

    def _resolve_domain(self):
        if self.valid_domain:
            return self.valid_domain

        domains_to_try = [self.url] + self.FALLBACK_DOMAINS
        for domain in domains_to_try:
            if self._is_dt_domain(domain):
                self.valid_domain = domain
                return self.valid_domain

        for domain in self._telegram_domains():
            if self._is_dt_domain(domain):
                self.valid_domain = 'https://' + domain if not domain.startswith('http') else domain
                return self.valid_domain

        self.valid_domain = self.url
        return self.valid_domain

    def _api_request(self, url, payload=None):
        headers = {
            'User-Agent': self.user_agent,
            'Content-Type': 'application/json; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
        }
        req = urllib.request.Request(url, data=payload, headers=headers)
        response = self.opener.open(req, timeout=20)
        return response.read().decode('utf-8', errors='ignore')

    def _post_search(self, domain, term):
        data = urllib.parse.urlencode({'valor': term}).encode()
        req = urllib.request.Request(domain + '/buscar', data=data, headers={'User-Agent': self.user_agent, 'Content-Type': 'application/x-www-form-urlencoded'})
        response = self.opener.open(req, timeout=20)
        html = response.read().decode('utf-8', errors='ignore')

        if 'anubis_challenge' in html:
            if self._solve_anubis(html, domain + '/buscar'):
                req = urllib.request.Request(domain + '/buscar', data=data, headers={'User-Agent': self.user_agent, 'Content-Type': 'application/x-www-form-urlencoded'})
                response = self.opener.open(req, timeout=20)
                html = response.read().decode('utf-8', errors='ignore')

        return html

    def _solve_anubis(self, html, original_url):
        match = re.search(r'<script id="anubis_challenge"[^>]*>(\{[\s\S]*?\})\s*</script>', html)
        if not match:
            return False

        try:
            challenge_json = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            return False

        rules = challenge_json.get('rules', {})
        challenge = challenge_json.get('challenge', {})

        difficulty = rules.get('difficulty', 5)
        random_data = challenge.get('randomData', '')
        challenge_id = challenge.get('id', '')
        method = challenge.get('method', 'fast')

        parsed_url = urllib.parse.urlparse(original_url)
        protocol = parsed_url.scheme
        domain = parsed_url.netloc
        redir = parsed_url.path
        if parsed_url.query:
            redir += '?' + parsed_url.query

        solution = self.anubis_solver.solve({
            'method': method,
            'difficulty': difficulty,
            'randomData': random_data
        })

        pass_url = f"{protocol}://{domain}/.within.website/x/cmd/anubis/api/pass-challenge?id={urllib.parse.quote(challenge_id)}&response={solution['response']}&nonce={solution['nonce']}&elapsedTime={solution['elapsedTime']}&redir={urllib.parse.quote(redir)}"

        try:
            req = urllib.request.Request(pass_url, headers={'User-Agent': self.user_agent})
            self.no_redirect_opener.open(req, timeout=10)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get_all('Set-Cookie'):
                self.cj.extract_cookies(e, req)
                return True
            return False
        except Exception:
            return False
        return True

    def _fetch_with_anubis(self, url):
        domain = self._resolve_domain()
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme:
            url = domain + url

        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
            response = self.opener.open(req, timeout=15)
            html = response.read().decode('utf-8', errors='ignore')

            if 'anubis_challenge' in html:
                if self._solve_anubis(html, url):
                    req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
                    response = self.opener.open(req, timeout=15)
                    html = response.read().decode('utf-8', errors='ignore')

            return html
        except Exception:
            return ''

    def _get_protected_download_url(self, detail_html, domain):
        match = re.search(r'data-content-id="(\d+)"[^>]*data-tabla="([^"]+)"', detail_html)
        if not match:
            match = re.search(r'data-tabla="([^"]+)"[^>]*data-content-id="(\d+)"', detail_html)
            if match:
                tabla, content_id = match.groups()
            else:
                return None
        else:
            content_id, tabla = match.groups()

        try:
            payload = json.dumps({'action': 'generate', 'content_id': int(content_id), 'tabla': tabla}).encode()
            gen_raw = self._api_request(domain + '/api_validate_pow.php', payload)
            gen = json.loads(gen_raw)
            if not gen.get('success') or not gen.get('challenge'):
                return None

            challenge = gen['challenge']
            nonce = 0
            while True:
                hh = hashlib.sha256((challenge + str(nonce)).encode()).hexdigest()
                if hh.startswith('000'):
                    break
                nonce += 1

            payload = json.dumps({'action': 'validate', 'challenge': challenge, 'nonce': nonce}).encode()
            val_raw = self._api_request(domain + '/api_validate_pow.php', payload)
            val = json.loads(val_raw)
            if not val.get('success') or not val.get('download_url'):
                return None

            dl = val['download_url']
            if dl.startswith('//'):
                return 'https:' + dl
            if dl.startswith('/'):
                return domain + dl
            return dl
        except Exception:
            return None

    def _get_bytes_with_anubis(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
        response = self.opener.open(req, timeout=20)
        data = response.read()

        if not data[:1] == b'd':
            try:
                html = data.decode('utf-8', errors='ignore')
                if 'anubis_challenge' in html and self._solve_anubis(html, url):
                    req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
                    response = self.opener.open(req, timeout=20)
                    data = response.read()
            except Exception:
                pass
        return data

    def download_torrent(self, url):
        domain = self._resolve_domain()
        if url.startswith('//'):
            url = 'https:' + url
        elif not url.startswith('http'):
            url = domain + url

        try:
            if '/torrents/' in url or url.endswith('.torrent'):
                torrent_data = self._get_bytes_with_anubis(url)
            else:
                detail_html = self._fetch_with_anubis(url)
                if not detail_html:
                    return
                dl_url = self._get_protected_download_url(detail_html, domain)
                if not dl_url:
                    return
                torrent_data = self._get_bytes_with_anubis(dl_url)

            if not torrent_data or torrent_data[:1] != b'd':
                return

            tmp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.torrent', delete=False)
            tmp_file.write(torrent_data)
            tmp_file.close()
            print(f"{tmp_file.name} {url}")
            sys.stdout.flush()
        except Exception:
            pass

    def search(self, what, cat='all'):
        domain = self._resolve_domain()
        html = self._post_search(domain, what)

        if not html:
            return

        anchors = re.findall(r'<a[^>]*class="[^"]*text-decoration-none[^"]*"[^>]*>[\s\S]*?</a>', html)

        for anchor in anchors:
            href_match = re.search(r'href=[\'"]([^\'"]+)[\'"]', anchor)
            if not href_match:
                continue
            href = href_match.group(1)
            if not (href.startswith('/pelicula/') or href.startswith('/serie/') or href.startswith('/series/')):
                continue

            name = re.sub(r'<[^>]+>', '', anchor).strip()

            item_url = domain + href

            item = {}
            item['seeds'] = '-1'
            item['leech'] = '-1'
            item['engine_url'] = domain
            item['desc_link'] = item_url
            item['link'] = item_url
            item['name'] = name.strip()

            detail_html = self._fetch_with_anubis(item_url)
            if detail_html:
                size_match = re.search(r'Tama[ñn]o:</b>\s*([^<]*?)\s*</p>', detail_html, re.IGNORECASE | re.DOTALL)
                if not size_match:
                    size_match = re.search(r'Tama[ñn]o:</b>\s*([^<]+)', detail_html, re.IGNORECASE | re.DOTALL)
                if size_match:
                    item['size'] = size_match.group(1).replace(',', '.').strip()
                    if not re.search(r'\d', item['size']):
                        item['size'] = '-1'
                else:
                    item['size'] = '-1'
            else:
                item['size'] = '-1'

            prettyPrinter(item)
