import re

import aiohttp
import bs4
from aiohttp import web


def find_words(s):
    return re.findall(r'\w+', s)


def is_habr_url(url):
    first_slash = url.find('/')
    url_without_http = url[first_slash + 2:]
    return url_without_http.startswith('habr.com')


def change_text(s):
    words = find_words(s)
    changed_words = []
    for word in words:
        if len(word) == 6:
            changed_words.append((word, word + '™'))
    for word, change_to in changed_words:
        s = s.replace(word, change_to)
    return s


def change_text_on_page(page):
    text_elements = page.find_all(text=True)
    blacklist = ['[document]',
                 'noscript',
                 'header',
                 'html',
                 'meta',
                 'head',
                 'input',
                 'script',
                 'style']

    valid_text_elements = filter(
        lambda x: x.parent.name not in blacklist, text_elements)
    for valid_element in valid_text_elements:
        if len(valid_element) > 5:
            text = change_text(str(valid_element))
            valid_element.replace_with(text)


def get_response_for_html(text):
    page = bs4.BeautifulSoup(text)

    for a in page.find_all('a'):
        if is_habr_url(a.get('href', '')):
            a['href'] = a['href']. \
                replace('habr.com', '127.0.0.1:8080'). \
                replace('https', 'http')
    change_text_on_page(page)
    return page


async def fetch_habr_page(session, params):
    url = f'https://habr.com{params}'
    async with session.get(url) as response:
        proxy_response_headers = [
            (name, value)
            for name, value
            in response.headers.items()
            if name.upper() not in ('CONTENT-ENCODING', 'TRANSFER-ENCODING')]
        if 'text/html' not in response.headers['Content-Type']:
            return web.Response(headers=proxy_response_headers,
                                status=response.status,
                                body=await response.read())
        text = await response.text()
        status = response.status
    page = get_response_for_html(text)
    print(proxy_response_headers)
    proxied_response = web.Response(
        status=status,
        text=str(page),
        headers=proxy_response_headers)

    # Copy response headers, except for Content-Encoding header,
    # since unfortunately aiohttp transparently decodes content.
    return proxied_response


async def handle(request):
    params = request.path_qs
    print('New request', params)
    async with aiohttp.ClientSession() as session:
        return await fetch_habr_page(session, params)


app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/{tail:.*}', handle)])

if __name__ == '__main__':
    web.run_app(app)
