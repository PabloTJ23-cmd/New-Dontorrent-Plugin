#VERSION: 2.00
# AUTHORS: Daniel Naranjo (garcianaranjodaniel@gmail.com)
# LICENSING INFORMATION

from novaprinter import prettyPrinter
import re
import json
import hashlib
import time
import tempfile
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


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
            elapsed = difficulty * 0.08
            time.sleep(elapsed)
            response = hashlib.sha256(random_data.encode()).hexdigest()
            return {'response': response, 'nonce': 0, 'elapsedTime': elapsed}
        else:
            target_zeros = difficulty
            nonce = 0
            while True:
                hash_input = (random_data + str(nonce)).encode()
                hash_hex = hashlib.sha256(hash_input).hexdigest()
                if hash_hex.startswith('0' * target_zeros):
                    return {'response': hash_hex, 'nonce': nonce, 'elapsedTime': 0.0}
                nonce += 1


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
        opener = urllib.request.build_opener(handler, urllib.request.HTTPRedirectHandler())
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')]
        self.opener = opener
        self.no_redirect_opener = urllib.request.build_opener(_NoRedirect())
        self.valid_domain = None
        self.anubis_solver = AnubisSolver()
    
    def _resolve_domain(self):
        if self.valid_domain:
            return self.valid_domain
        
        domains_to_try = [self.url] + self.FALLBACK_DOMAINS
        for domain in domains_to_try:
            try:
                req = urllib.request.Request(domain, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
                response = self.opener.open(req, timeout=10)
                content = response.read().decode('utf-8', errors='ignore')
                if 'anubis_challenge' in content or 'DonTorrent' in content or 'pelicula' in content.lower():
                    self.valid_domain = domain
                    return domain
            except Exception:
                continue
        
        self.valid_domain = self.url
        return self.valid_domain
    
    def _solve_anubis(self, html, original_url):
        match = re.search(r'<script[^>]*id="anubis_challenge"[^>]*>\s*(\{[\s\S]*?\})\s*</script>', html)
        if not match:
            return False
        
        try:
            challenge_json = json.loads(match.group(1))
        except json.JSONDecodeError:
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
        
        pass_url = f"{protocol}://{domain}/.within.website/x/cmd/anubis/api/pass-challenge?id={challenge_id}&response={solution['response']}&nonce={solution['nonce']}&elapsedTime={solution['elapsedTime']}&redir={urllib.parse.quote(redir)}"
        
        try:
            req = urllib.request.Request(pass_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
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
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
            response = self.opener.open(req, timeout=15)
            html = response.read().decode('utf-8', errors='ignore')
            
            if 'anubis_challenge' in html:
                if self._solve_anubis(html, url):
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
                    response = self.opener.open(req, timeout=15)
                    html = response.read().decode('utf-8', errors='ignore')
            
            return html
        except Exception:
            return ''
    
    def download_torrent(self, url):
        domain = self._resolve_domain()
        if not url.startswith('http'):
            url = domain + url
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
            response = self.opener.open(req, timeout=15)
            torrent_data = response.read()
            
            if not torrent_data.startswith(b'd8:') or b'anubis_challenge' in torrent_data:
                html_decoded = torrent_data.decode('utf-8', errors='ignore')
                if 'anubis_challenge' in html_decoded:
                    if self._solve_anubis(html_decoded, url):
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
                        response = self.opener.open(req, timeout=15)
                        torrent_data = response.read()
            
            tmp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.torrent', delete=False)
            tmp_file.write(torrent_data)
            tmp_file.close()
            print(tmp_file.name)
        except Exception:
            pass
    
    def search(self, what, cat='all'):
        domain = self._resolve_domain()
        search_term = what.replace('+', '%20').replace(' ', '%20')
        search_url = f"{domain}/buscar/{search_term}"
        html = self._fetch_with_anubis(search_url)
        
        if not html:
            return
        
        quantity_match = re.findall(r'<p.*?class="lead.*?</p>', html)
        try:
            quantity = re.findall(r'<b>(.*?)</b>', quantity_match[1])[0]
            quantity = int(quantity.replace(',', '').replace('.', ''))
        except (IndexError, ValueError):
            quantity = 0
        
        if quantity > 0:
            pages = re.findall(r'<a.*?class="page-link.*?</a>', html)
            if len(pages) > 2:
                pages = pages[1:-1]
                pages = len(pages)
            else:
                pages = 0
        else:
            pages = 0
        
        links = []
        
        for i in range(2, pages + 1):
            url = f"{domain}/buscar/{search_term}/page/{i}"
            html = self._fetch_with_anubis(url)
            
            a_list = re.findall(r'<a.*?class="text-decoration-none.*?</a>', html)
            for a in a_list:
                url_match = re.findall(r'href=[\'"]?([^\'" >]+)', a)
                if len(url_match) > 0:
                    links.append(url_match[0])
        
        html = self._fetch_with_anubis(search_url)
        a_list = re.findall(r'<a.*?class="text-decoration-none.*?</a>', html)
        for a in a_list:
            url_match = re.findall(r'href=[\'"]?([^\'" >]+)', a)
            if len(url_match) > 0:
                links.append(url_match[0])
        
        for i in links:
            if i.startswith('/'):
                item_url = domain + i
            else:
                item_url = i
            
            html = self._fetch_with_anubis(item_url)
            if not html:
                continue
            
            item = {}
            item['seeds'] = '-1'
            item['leech'] = '-1'
            item['engine_url'] = domain
            item['desc_link'] = item_url
            
            name_part = i.rstrip('/').split('/')[-1].replace("-", " ")
            item['name'] = name_part
            
            if '/serie' not in i and '/series' not in i:
                tam = re.findall(r'<p.*?class="mb-0.*?</p>', html)
                
                if len(tam) > 0:
                    if len(tam) >= 2:
                        tam = tam[1]
                    else:
                        tam = tam[0]
                    
                    try:
                        content = tam[tam.rfind("b")+2 : tam.rfind("<")]
                        content = content.strip()
                    except:
                        content = "-1"
                    
                    content = content.replace(",", ".")
                    item['size'] = content
                else:
                    item['size'] = "-1"
                
                download_link = re.findall(r'<a.*?class="text-white bg-primary rounded-pill d-block shadow text-decoration-none p-1.*?</a>', html)
                
                if len(download_link) == 0:
                    download_link = re.findall(r'<a.*?class="text-white bg-primary rounded-pill d-block shadow-sm text-decoration-none my-1 py-1.*?</a>', html)
                
                if len(download_link) > 0:
                    dl_match = re.findall(r'href=[\'"]?([^\'" >]+)', download_link[0])
                    if len(dl_match) > 0:
                        dl_href = dl_match[0]
                        if dl_href.startswith('//'):
                            item['link'] = 'https:' + dl_href
                        elif dl_href.startswith('/'):
                            item['link'] = domain + dl_href
                        else:
                            item['link'] = dl_href
                
                prettyPrinter(item)
            else:
                tds = re.findall(r'<tr>(.*?)</tr>', html, re.M|re.I|re.S)
                tds = tds[1:]
                for td in tds:
                    td_content = re.findall(r'<td.*?>(.*?)</td>', td, re.DOTALL)
                    if len(td_content) >= 2:
                        a = td_content[1]
                        
                        try:
                            dl_match = re.findall(r'href=[\'"]?([^\'" >]+)', a)
                            if len(dl_match) > 0:
                                dl_href = dl_match[0]
                                if dl_href.startswith('//'):
                                    item['link'] = 'https:' + dl_href
                                elif dl_href.startswith('/'):
                                    item['link'] = domain + dl_href
                                else:
                                    item['link'] = dl_href
                                
                                item['size'] = '-1'
                                item['name'] = name_part + " " + td_content[0]
                                prettyPrinter(item)
                        except:
                            continue
