# misis-elibrary

Программа для загрузки книг из электронной библиотеки МИСИС.

## Установка

```sh
pip install misis-elibrary
```

## Использование

```
usage: misis-elibrary [-h] -l Логин -p Пароль [-i ID] [-d Директория] [Запрос ...]

Программа для загрузки книг из электронной библиотеки МИСИС.

positional arguments:
  Запрос                Запрос для поиска

options:
  -h, --help            show this help message and exit
  -l Логин, --login Логин
  -p Пароль, --password Пароль
  -i ID, --id ID        ID книги
  -d Директория, --directory Директория
                        Директория для загрузки книг. Если не указана, то используется текущая
```
