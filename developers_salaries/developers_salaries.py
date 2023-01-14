from environs import Env
import requests
from urllib import parse
from itertools import count
from terminaltables import AsciiTable
from collections.abc import Iterator, Iterable


class Vacancy():
    def __init__(self,
                 language: str,
                 currency: str,
                 salary_from: int | None,
                 salary_to: int | None
                 ) -> None:
        self.language: str = language
        self.currency: str = currency
        self.salary_from: int | None = salary_from
        self.salary_to: int | None = salary_to
        self.average_salary: int | None = self._count_average_salary()

    def __str__(self) -> str:
        return (f'{self.language} - '
                f'{self.currency} - '
                f'{self.salary_from} - '
                f'{self.salary_to} - '
                f'{self.average_salary}')

    def __repr__(self) -> str:
        return self.__str__()

    def _count_average_salary(self) -> int | None:
        match self.currency, self.salary_from, self.salary_to:
            case 'RUR' | 'rub', int() as salary_from, int() as salary_to:
                return int((salary_from + salary_to)/2)
            case 'RUR' | 'rub', None, int() as salary_to:
                return int(salary_to * 0.8)
            case 'RUR' | 'rub', int() as salary_from, None:
                return int(salary_from * 1.2)
            case _:
                return None


class VacanciesPortal():
    def __init__(self, portal_name: str) -> None:
        self.portal_name: str = portal_name
        self.vacancies: list = []
        self.LANGUAGES: Iterable = ()

    def print_languages_stats_table(self) -> None:
        table_data: list = [('Язык программирования',
                             'Вакансий найдено',
                             'Вакансий обработано',
                             'Средняя зарплата')]
        for language in self.LANGUAGES:
            language_stats: tuple | None = self._get_language_stats(language)
            if language_stats:
                table_data.append(language_stats)
        table_instance: AsciiTable = AsciiTable(table_data, self.portal_name)
        print(table_instance.table)

    def _get_language_stats(self, language: str) -> tuple[str, int, int, int]:
        found: int = 0
        processed: int = 0
        salaries_sum: int = 0
        for vacancy in self.vacancies:
            if vacancy.language == language:
                found += 1
                if vacancy.average_salary:
                    salaries_sum += vacancy.average_salary
                    processed += 1
        if found and processed:
            return language, found, processed, int((salaries_sum/processed))
        elif found:
            return language, found, 0, 0
        else:
            return language, 0, 0, 0


class HeadHunter(VacanciesPortal):
    def __init__(self, languages: Iterable) -> None:
        super().__init__('HeadHunter')
        self.API_URL: str = 'https://api.hh.ru/'
        self.LANGUAGES: Iterable[str] = languages
        for language in self.LANGUAGES:
            self._get_vacancies_by_language(language)

    @staticmethod
    def _fetch_records(url: str, params: dict) -> Iterator:
        for page in count():
            params['page'] = page
            page_response: requests.Response = requests.get(url, params)
            page_response.raise_for_status()
            page_payload: dict = page_response.json()
            yield from page_payload['items']
            if page >= page_payload['pages'] - 1:
                break

    def _get_vacancies_by_language(self, language: str) -> None:
        vacancies_url: str = parse.urljoin(self.API_URL, 'vacancies')
        params: dict[str, str] = {
            'text': f'Программист {language}',
            'area': '1',
            'professional_role': '96',
            'only_with_salary': 'true',
        }
        for vacancy in self._fetch_records(vacancies_url,
                                           params):
            self.vacancies.append(
                Vacancy(language=language,
                        currency=vacancy['salary']['currency'],
                        salary_from=vacancy['salary']['from'],
                        salary_to=vacancy['salary']['to'])
                )


class SuperJob(VacanciesPortal):
    def __init__(self, languages: Iterable, client_secret: str) -> None:
        super().__init__('SuperJob')
        self.API_URL: str = 'https://api.superjob.ru'
        self.LANGUAGES: Iterable[str] = languages
        self.CLIENT_SECRET: str = client_secret
        for language in self.LANGUAGES:
            self._get_vacancies_by_language(language)

    @staticmethod
    def _fetch_records(url: str, params: dict, headers: dict) -> Iterator:
        for page in count():
            params['page'] = page
            page_response: requests.Response = requests.get(url=url,
                                                            params=params,
                                                            headers=headers)
            page_response.raise_for_status()
            page_payload: dict = page_response.json()
            yield from page_payload['objects']
            if not page_payload['more']:
                break

    def _get_vacancies_by_language(self, language: str) -> None:
        vacancies_url: str = parse.urljoin(self.API_URL, '2.0/vacancies')
        headers: dict[str, str] = {
            'X-Api-App-Id': self.CLIENT_SECRET,
        }
        params: dict[str, str] = {
            'keyword': f'Программист {language}',
            'town': 'Москва',
            'catalogues': '48',
            'no_agreement': '1',
            'count': '100',
        }
        for vacancy in self._fetch_records(vacancies_url,
                                           params,
                                           headers):
            self.vacancies.append(
                Vacancy(language=language,
                        currency=vacancy['currency'],
                        salary_from=vacancy['payment_from'],
                        salary_to=vacancy['payment_to'])
                )


if __name__ == '__main__':
    env: Env = Env()
    env.read_env()
    try:
        with open(env('LANGUAGES_FILE',
                      default='languages.txt'), 'r') as file:
            popular_languages: list = [line for line in
                                       file.read().splitlines()]
    except OSError:
        print("Can't open file languages file!")
    hh_portal: HeadHunter = HeadHunter(popular_languages)
    hh_portal.print_languages_stats_table()
    superjob: SuperJob = SuperJob(popular_languages,
                                  env('SUPERJOB_CLIENT_SECRET'))
    superjob.print_languages_stats_table()
