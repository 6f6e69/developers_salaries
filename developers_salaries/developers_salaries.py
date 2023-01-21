from environs import Env
import requests
from urllib import parse
from itertools import count
from collections.abc import Generator, Callable
from terminaltables import AsciiTable


def get_statistics_table(portal_name: str,
                         vacancies_salaries_generator: Callable
                         ) -> AsciiTable.table:
    table_rows: list = [('Язык программирования',
                         'Вакансий найдено',
                         'Вакансий обработано',
                         'Средняя зарплата')]
    for language in POPULAR_LANGUAGES:
        found: int = 0
        processed: int = 0
        salaries_sum: int = 0
        for salary in vacancies_salaries_generator(language):
            found += 1
            if salary:
                salaries_sum += salary
                processed += 1
        if found and processed:
            table_rows.append((language,
                               found,
                               processed,
                               int((salaries_sum/processed))))
        elif found:
            table_rows.append((language, found, 0, 0))
        else:
            table_rows.append((language, 0, 0, 0))
    return AsciiTable(table_rows, portal_name).table


def count_average_rur_salary(currency: str,
                             salary_from: str,
                             salary_to: str) -> int | None:
    match currency, salary_from, salary_to:
        case 'RUR' | 'rub', int() as salary_from, int() as salary_to:
            return int((salary_from + salary_to)/2)
        case 'RUR' | 'rub', None, int() as salary_to:
            return int(salary_to * 0.8)
        case 'RUR' | 'rub', int() as salary_from, None:
            return int(salary_from * 1.2)
        case _:
            return None


def get_hh_vacancies_avg_salary(language: str) -> Generator[int | None,
                                                            None,
                                                            None]:
    API_URL: str = 'https://api.hh.ru/'
    VACANCIES_URL: str = parse.urljoin(API_URL, 'vacancies')
    DEVELOPER_PROFESSION_ROLE_ID: str = '96'
    MOSCOW_TOWN_ID: str = '1'
    params: dict[str, str | int] = {
            'text': f'Программист {language}',
            'area': MOSCOW_TOWN_ID,
            'professional_role': DEVELOPER_PROFESSION_ROLE_ID,
            'only_with_salary': 'true',
        }
    for page in count():
        params['page'] = page
        page_response: requests.Response = requests.get(url=VACANCIES_URL,
                                                        params=params)
        page_response.raise_for_status()
        page_payload: dict = page_response.json()
        for vacancy in page_payload['items']:
            vacancy_average_salary: int | None = count_average_rur_salary(
                                                 vacancy['salary']['currency'],
                                                 vacancy['salary']['from'],
                                                 vacancy['salary']['to'])
            yield vacancy_average_salary
        if page >= page_payload['pages'] - 1:
            break


def get_superjob_vacancies_avg_salary(language: str) -> Generator[int | None,
                                                                  None,
                                                                  None]:
    API_URL: str = 'https://api.superjob.ru'
    VACANCIES_URL: str = parse.urljoin(API_URL, '2.0/vacancies')
    DEVELOPMENT_CATALOGUE_ID: str = '48'
    headers: dict[str, str] = {
        'X-Api-App-Id': SUPERJOB_CLIENT_SECRET,
    }
    params: dict[str, str | int] = {
        'keyword': f'Программист {language}',
        'town': 'Москва',
        'catalogues': DEVELOPMENT_CATALOGUE_ID,
        'no_agreement': '1',
        'count': '100',
    }
    for page in count():
        params['page'] = page
        page_response: requests.Response = requests.get(url=VACANCIES_URL,
                                                        params=params,
                                                        headers=headers)
        page_response.raise_for_status()
        page_payload: dict = page_response.json()
        for vacancy in page_payload['objects']:
            vacancy_average_salary: int | None = count_average_rur_salary(
                                                 vacancy['currency'],
                                                 vacancy['payment_from'],
                                                 vacancy['payment_to'])
            yield vacancy_average_salary
        if not page_payload['more']:
            break


if __name__ == '__main__':
    env: Env = Env()
    env.read_env()
    SUPERJOB_CLIENT_SECRET: str = env('SUPERJOB_CLIENT_SECRET')
    try:
        with open(env('LANGUAGES_FILE', default='languages.txt'), 'r') as file:
            POPULAR_LANGUAGES: list = [line for line
                                       in file.read().splitlines()]
    except OSError:
        print("Can't open languages file!")
    hh_table: AsciiTable = get_statistics_table(
                                    'HeadHunter',
                                    get_hh_vacancies_avg_salary)
    print(hh_table)
    superjob_table: AsciiTable = get_statistics_table(
                                     'SuperJob',
                                     get_superjob_vacancies_avg_salary)
    print(superjob_table)
