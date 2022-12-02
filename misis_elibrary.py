#!/usr/bin/env python3

__prog__ = "misis-elibrary"
__desc__ = "Программа для загрузки книг из электронной библиотеки МИСИС."
__version__ = "0.0.2"

import argparse
import imghdr
import sys
from dataclasses import dataclass
from pathlib import Path

import img2pdf
import requests
from bs4 import BeautifulSoup
from requests.cookies import RequestsCookieJar

BASE_URL = "http://elibrary.misis.ru/"
SEARCH_URL = BASE_URL + "search2.php?action=process"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
}


def soup(text: str):
    return BeautifulSoup(text, "html.parser")


def login_failed(page: requests.Response) -> bool:
    return (
        "Пароль не верен. Пожалуйста, проверьте Ваше Имя и Пароль и попробуйте еще." in page.text
    )


def page_invalid(page: requests.Response) -> bool:
    # Являются ли возвращённые данные чем-то, кроме jpeg изображения
    return imghdr.tests[0](page.content, None) is None


def get_metadata_url(id: int) -> str:
    return f"{BASE_URL}view.php?fDocumentId={id}"


def get_request_url(id: int, page: int, request: str) -> str:
    return f"{BASE_URL}plugins/SecView/{request}.php?id={id}&page={page}&type=large/fast"


def get_page_url(id: int, page: int) -> str:
    return get_request_url(id, page, "getDoc")


def get_hash_url(id: int, page: int) -> str:
    return get_request_url(id, page, "HashAvailability")


def get_path(user_path: Path, metadata: dict[str, str]) -> Path:
    if user_path.is_dir():
        return user_path / f'{metadata["Название"]}.pdf'
    else:
        return user_path


def check_path(user_path: Path):
    if not user_path.is_dir() and not user_path.parent.exists:
        raise FileNotFoundError(f"No such file or directory: '{user_path}'")


def auth(
    login: str, password: str, redirect_url: str = ""
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
    response = requests.post(LOGIN_URL, payload, cookies=session, headers=HEADERS)
    if login_failed(response):
        print(f"Не удалось войти.", file=sys.stderr)
        exit(3)
    return session, response


@dataclass
class Book:
    id: int
    title: str
    authors: str
    year: int


def search(query: str, session: RequestsCookieJar) -> list[Book]:
    query = query.replace('"', "'")
    payload = {
        "txtQuery": f'(GeneralText contains "{query}")',
        "cbQuickQuery": 1,
        "cbQuickGeneral": 1,
    }
    session["__kt_batch_size"] = "1024"  # Не думаю, что кому-нибудь понадобится больше результатов
    search_response = requests.post(SEARCH_URL, payload, cookies=session, headers=HEADERS)
    del session["__kt_batch_size"]
    content = soup(search_response.text).find("div", id="content")
    table = content.find("table", class_="kt_collection")

    search_results: list[Book] = []
    for row in table.find("tbody").find_all("tr"):
        columns = list(row.find_all("td"))
        link = columns[1].find("a")
        search_results.append(
            Book(
                id=int(link["href"].split("=")[-1]),
                title=link.text,
                authors=columns[3].text.strip(),
                year=int(columns[4].text.strip()),
            )
        )
    return search_results


def print_search_results(search_results: list[Book]):
    for i in range(len(search_results)):
        book = search_results[len(search_results) - i - 1]
        print(
            f"{len(search_results) - i}. {book.authors}{' - ' if book.authors else ''}{book.title} ({book.year})"
        )


def get_search_result(search_results: list[Book]) -> Book:
    return search_results[int(input("> ")) - 1]


def get_metadata(id: int, metadata_response: requests.Response | None) -> dict[str, str] | None:
    if metadata_response is None:
        metadata_response = requests.get(get_metadata_url(id), headers=HEADERS)
    content = soup(metadata_response.text).find("div", id="content")

    metadata: dict[str, str] = {}
    if title_string := content.find("h2"):
        metadata["Название"] = title_string.text[len("Сведения по Документу: ") :]
    else:
        return None

    table = content.find("table", class_="metadatatable")
    for row in table.find_all("tr"):
        metadata[row.find("th").text] = row.find("td").text.strip()

    return metadata


def print_metadata(metadata: dict[str, str]) -> None:
    for key, value in metadata.items():
        print(key, ": ", value, sep="")


def download(
    id: int, session: RequestsCookieJar, first_hash_response: requests.Response | None = None
) -> bytes:
    """
    Функция возвращает pdf файл
    """
    if first_hash_response is None:
        first_hash_response = requests.get(get_hash_url(id, 0), cookies=session, headers=HEADERS)

    if first_hash_response.text != "0":
        print(f"Нет книги с ID {id}.", file=sys.stderr)
        exit(2)

    sys.stdout.write(f"Загружаем 1 страницу...")
    first_page = requests.get(get_page_url(id, 0), cookies=session, headers=HEADERS)
    pages = [first_page.content]
    sys.stdout.flush()

    i = 1
    while True:
        requests.get(get_hash_url(id, i), cookies=session, headers=HEADERS)
        sys.stdout.write(f"\rЗагружаем {i + 1} страницу...")
        page = requests.get(get_page_url(id, i), cookies=session, headers=HEADERS)
        sys.stdout.flush()
        if page_invalid(page):
            break
        i += 1
        pages.append(page.content)
    sys.stdout.write(f"\rСтраниц загружено: {i}\n")

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
    parser.add_argument("-i", "--id", required=False, type=int, metavar="ID", help="ID книги")
    parser.add_argument(
        "-o",
        "--output-path",
        type=str,
        default=".",
        metavar="Путь",
        help="Может быть путём как к существующей директории, так и к файлу.",
    )
    parser.add_argument(
        "query",
        metavar="Запрос",
        type=str,
        nargs="*",
        help="Запрос для поиска",
    )

    args = parser.parse_args()
    args.query = " ".join(args.query).strip()

    path = Path(args.output_path)
    check_path(Path(args.output_path))

    if args.query:
        session, _ = auth(args.login, args.password)

        search_results = search(args.query, session)
        print_search_results(search_results)
        args.id = get_search_result(search_results).id
    elif args.id is None:
        print("Передайте программе либо ID, либо запрос.", file=sys.stderr)
        exit(1)
    else:
        if args.id <= 0:
            print("Передан некорректный ID", file=sys.stderr)
            exit(1)


    session, metadata_response = auth(args.login, args.password, get_metadata_url(args.id))

    metadata = get_metadata(args.id, metadata_response)
    if metadata is None:
        print(f"Нет книги с ID {id}.", file=sys.stderr)
        exit(2)
    print_metadata(metadata)

    path = get_path(path, metadata)
    print(f"Загружаем книгу в '{path}'...")

    pdf = download(args.id, session)
    with open(path, "wb") as f:
        f.write(pdf)


if __name__ == "__main__":
    main()
