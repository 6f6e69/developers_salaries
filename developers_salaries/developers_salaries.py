from environs import Env
import requests
from urllib import parse
from itertools import count
from collections.abc import Generator, Callable
from terminaltables import AsciiTable
from functools import partial


def get_statistics_table(portal_name: str,
                         popular_languages: list,
                         vacancies_salaries_generator: Callable
                         ) -> AsciiTable.table:
    table_rows: list = [('Язык программирования',
                         'Вакансий найдено',
                         'Вакансий обработано',
                         'Средняя зарплата')]
    for language in popular_languages:
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
    api_url: str = 'https://api.hh.ru/'
    vacancies_url: str = parse.urljoin(api_url, 'vacancies')
    developer_profession_id: str = '96'
    moscow_town_id: str = '1'
    params: dict[str, str | int] = {
            'text': f'Программист {language}',
            'area': moscow_town_id,
            'professional_role': developer_profession_id,
            'only_with_salary': 'true',
        }
    for page in count():
        params['page'] = page
        page_response: requests.Response = requests.get(url=vacancies_url,
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


def get_superjob_vacancies_avg_salary(language: str,
                                      api_key: str) -> Generator[int | None,
                                                                 None,
                                                                 None]:
    api_url: str = 'https://api.superjob.ru'
    vacancies_url: str = parse.urljoin(api_url, '2.0/vacancies')
    development_catalogue_id: str = '48'
    headers: dict[str, str] = {
        'X-Api-App-Id': api_key,
    }
    params: dict[str, str | int] = {
        'keyword': f'Программист {language}',
        'town': 'Москва',
        'catalogues': development_catalogue_id,
        'no_agreement': '1',
        'count': '100',
    }
    for page in count():
        params['page'] = page
        page_response: requests.Response = requests.get(url=vacancies_url,
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


def main() -> None:
    env: Env = Env()
    env.read_env()
    superjob_client_secret: str = env('SUPERJOB_CLIENT_SECRET')
    try:
        with open(env('LANGUAGES_FILE', default='languages.txt'), 'r') as file:
            popular_languages: list = [line for line
                                       in file.read().splitlines()]
    except OSError:
        print("Can't open languages file!")
    hh_table: AsciiTable.table = get_statistics_table(
                                    'HeadHunter',
                                    popular_languages,
                                    get_hh_vacancies_avg_salary)
    print(hh_table)
    get_superjob_vacancies_avg_salary_no_api_key: partial = partial(
                                             get_superjob_vacancies_avg_salary,
                                             api_key=superjob_client_secret)
    superjob_table: AsciiTable.table = get_statistics_table(
                                  'SuperJob',
                                  popular_languages,
                                  get_superjob_vacancies_avg_salary_no_api_key)
    print(superjob_table)


if __name__ == '__main__':
    main()
