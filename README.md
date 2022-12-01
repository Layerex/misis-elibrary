# misis-elibrary

Программа для загрузки книг из электронной библиотеки МИСИС.

## Установка

``` sh
pip install misis-elibrary
```

## Использование

```
usage: misis-elibrary [-h] -l Логин -p Пароль -i ID [-o Путь]

Программа для загрузки книг из электронной библиотеки МИСИС.

options:
  -h, --help            show this help message and exit
  -l Логин, --login Логин
  -p Пароль, --password Пароль
  -i ID, --id ID        ID книги
  -o Путь, --output-path Путь
                        Может быть путём как к существующей директории, так и к файлу. По умолчанию файл сохраняется в {id}.pdf
```

