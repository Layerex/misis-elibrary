#!/usr/bin/env python3

__prog__ = "misis-elibrary"
__desc__ = "Программа для загрузки книг из электронной библиотеки МИСИС."
__version__ = "0.0.1"

import argparse
import imghdr
import os
import sys
from pathlib import Path

import img2pdf
import requests
from requests.cookies import RequestsCookieJar

BASE_URL = "http://elibrary.misis.ru/"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
}


def login_failed(page: requests.Response) -> bool:
    return (
        "Пароль не верен. Пожалуйста, проверьте Ваше Имя и Пароль и попробуйте еще." in page.text
    )


def page_invalid(page: requests.Response) -> bool:
    # Являются ли возвращённые данные чем-то, кроме jpeg изображения
    return imghdr.tests[0](page.content, None) is None


def get_request_url(id: int, page: int, request: str) -> str:
    return f"{BASE_URL}plugins/SecView/{request}.php?id={id}&page={page}&type=large/fast"


def get_page_url(id: int, page: int) -> str:
    return get_request_url(id, page, "getDoc")


def get_hash_url(id: int, page: int) -> str:
    return get_request_url(id, page, "HashAvailability")


def get_path(user_path: Path, id: int) -> Path:
    if user_path.is_dir():
        return user_path / f"{id}.pdf"
    if os.path.exists(user_path.parent):
        return user_path
    raise FileNotFoundError(f"No such file or directory: '{user_path}'")


def auth(
    login: str, password: str, redirect_url: str
) -> tuple[RequestsCookieJar, requests.Response]:
    """
    Функция возвращает сессию и ответ на запрос к redirect_url
    """
    LOGIN_URL = BASE_URL + "login.php"
    response = requests.get(LOGIN_URL, headers=HEADERS)
    session = response.cookies
    payload = {
        "action": "login",
        "cookieverify": "",
        "redirect": redirect_url,
        "username": login,
        "password": password,
        "language": "ru_UN",
    }
    response = requests.post(LOGIN_URL, payload, cookies=session)
    if login_failed(response):
        print(f"Не удалось войти.", file=sys.stderr)
        exit(3)
    return session, response


def download(id: int, session: RequestsCookieJar, first_hash_request: requests.Response) -> bytes:
    """
    Функция возвращает pdf файл
    """
    if first_hash_request.text != "0":
        print(f"Нет книги с ID {id}.", file=sys.stderr)
        exit(2)

    sys.stdout.write(f"Загружаем 1 страницу...")
    first_page = requests.get(get_page_url(id, 0), cookies=session)
    pages = [first_page.content]
    sys.stdout.flush()

    i = 1
    while True:
        requests.get(get_hash_url(id, i), cookies=session)
        sys.stdout.write(f"\rЗагружаем {i + 1} страницу...")
        page = requests.get(get_page_url(id, i), cookies=session)
        sys.stdout.flush()
        i += 1
        if page_invalid(page):
            break
        pages.append(page.content)
    sys.stdout.write(f"\rСтраниц загружено: {i - 1}")

    # Чтобы страницы не были слишком маленькими, устанавливаем формат A4
    a4layout = img2pdf.get_layout_fun((img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297)))
    return img2pdf.convert(pages, layout_fun=a4layout)


def main():
    parser = argparse.ArgumentParser(
        prog=__prog__,
        description=__desc__,
    )

    parser.add_argument("-l", "--login", required=True, type=str, metavar="Логин")
    parser.add_argument("-p", "--password", required=True, type=str, metavar="Пароль")
    parser.add_argument("-i", "--id", required=True, type=int, metavar="ID", help="ID книги")
    parser.add_argument(
        "-o",
        "--output-path",
        type=str,
        default=".",
        metavar="Путь",
        help="Может быть путём как к существующей директории, так и к файлу. По умолчанию файл сохраняется в {id}.pdf",
    )

    args = parser.parse_args()

    path = get_path(Path(args.output_path), args.id)
    session, auth_response = auth(args.login, args.password, get_hash_url(args.id, 0))
    pdf = download(args.id, session, auth_response)
    with open(path, "wb") as f:
        f.write(pdf)


if __name__ == "__main__":
    main()
