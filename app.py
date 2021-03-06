import requests
import json
import cities_id
from bs4 import BeautifulSoup
from cities_tree import CitiesTree
from comparison import compare
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class MainWindow(Gtk.Window):

    def __init__(self):
        super().__init__(title="Weather forecast from Yandex")
        self.connection = None
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_size_request(1000, 500)
        master_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(master_box)

        api_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.api_entry = Gtk.Entry()
        self.api_from_file()

        self.api_button = Gtk.Button(
            label='Изменить API-Key для Яндекс.Погоды'
        )
        self.api_button.connect('clicked', self.api_editable)
        api_box.pack_end(self.api_entry, False, True, 0)
        api_box.pack_end(self.api_button, False, True, 0)
        master_box.pack_start(api_box, False, True, 0)
        hpaned = Gtk.Paned()
        master_box.add(hpaned)
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.search_entry = Gtk.Entry()
        search_box.pack_start(self.search_entry, False, True, 0)
        self.search_button = Gtk.Button(label="Получить прогноз")
        self.search_button.connect('clicked', self.set_forecast_wiki)
        search_box.pack_start(self.search_button, False, True, 0)
        self.search_entry.connect('changed', self.entry_changed)
        left_box.pack_start(search_box, False, True, 0)
        hpaned.add1(left_box)
        hpaned.add2(right_box)
        cities_tree_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.cities = cities_id.cities().keys()
        self.cities_treeview = CitiesTree(self.cities)
        self.city_select = self.cities_treeview.get_selection()
        self.city_select.connect("changed", self.set_forecast_for_selection)
        cities_adj = Gtk.Adjustment()
        cities_scroll = Gtk.ScrolledWindow(cities_adj)
        cities_scroll.set_size_request(400, 500)
        cities_scroll.add_with_viewport(self.cities_treeview)
        left_box.pack_start(cities_tree_box, False, True, 0)
        cities_tree_box.pack_start(cities_scroll, True, True, 0)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        right_box.pack_end(button_box, False, True, 0)
        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", Gtk.main_quit)
        button_box.pack_start(close_button, True, True, 0)
        self.weather_info_label = Gtk.Label()
        self.weather_info_label.set_size_request(600, 400)
        self.weather_info_label.set_selectable(True)
        self.weather_info_label.set_line_wrap(True)
        weather_scroll = Gtk.ScrolledWindow()
        weather_scroll.set_size_request(600, 400)
        weather_scroll.add_with_viewport(self.weather_info_label)
        right_box.pack_start(weather_scroll, True, True, 0)
        self.selection_block = False
        self.api_iseditable = False
        self.api_entry.set_editable(False)

    def api_editable(self, button):
        if self.api_iseditable:
            self.api_entry.set_editable(False)
            self.api_iseditable = False
            self.api_button.set_label('Изменить API-Key для Яндекс.Погоды: ')
            with open('api', 'w') as file:
                file.write(self.api_entry.get_text())
            if self.search_entry.get_text() == '':
                self.search_entry.set_text(' ')
                self.search_entry.grab_focus()
                self.search_entry.set_text('')
            else:
                self.search_entry.grab_focus()
        else:
            self.api_entry.set_editable(True)
            self.api_iseditable = True
            self.api_button.set_label('ОК')
            self.api_entry.grab_focus()

    def api_from_file(self):
        try:
            with open('api', 'r') as file:
                self.api_entry.set_text(file.read())
        except Exception:
            pass

    def entry_changed(self, entry):
        self.selection_block = True
        selected_cities = []
        for city in self.cities:
            if entry.get_text().lower() in city.lower():
                selected_cities.append(city)
        self.cities_treeview.fill_store(selected_cities)

        if self.cities_treeview.selected_city:
            self.set_forecast_text(
                self.cities_treeview.selected_city,
                self.cities_treeview.selected_city
            )
        else:
            self.weather_info_label.set_text('')
        self.selection_block = False

    def set_forecast_text(self, city, city_orig):
        self.weather_info_label.set_text(
            'Получение данных, прогноз сформируется через несколько секунд'
        )
        c = City(city)
        c.get_wiki_html()
        c.get_wiki_descr()
        c.get_coordinates_dateandtime()
        c.get_yandex_crumbs()
        if (not c.longitude) or (not c.latitude):
            self.weather_info_label.set_text(
                'Проверьте введенное название города (' + city_orig + ')'
            )
        else:
            w = Weather(c, self.api_entry.get_text())
            w.send_request()
            w.get_json()
            forecast = w.json_parce_now() + ('\n\n') + w.json_parce_fore()
            if w.wrong_api:
                self.weather_info_label.set_text(w.check_api_message)
            else:
                self.weather_info_label.set_text(forecast)

    def set_forecast_wiki(self, button):
        city_orig = self.search_entry.get_text()
        city = self.search_entry.get_text().title()
        self.set_forecast_text(city, city_orig)

    def set_forecast_for_selection(self, selection):
        if not self.selection_block:
            model, treeiter = selection.get_selected()
            city = model[treeiter][0]
            self.set_forecast_text(city, city)


class City():

    def __init__(self, city):
        self.city = city
        self.init_city = city

    def get_wiki_html(self):
        city_full_name = self.city.title().replace('Город', 'город')
        ua = {
            'User-Agent': ('Mozilla/5.0 (Macintosh; '
                           'Intel Mac OS X 10_8_2) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/27.0.1453.116 '
                           'Safari/537.36')
        }
        url = 'https://ru.wikipedia.org/wiki/' + city_full_name + '#/maplink/0'
        self.url_wiki = url.replace('#/maplink/0', '')
        result = requests.get(url, headers=ua)
        wiki_html = BeautifulSoup(
            result.text, features="html.parser"
        )
        self.wiki_html = wiki_html
        self.get_coordinates_wiki()
        try:
            f_latitude = float(self.latitude)
            f_longitude = float(self.longitude)
        except ValueError:
            if '_(город)' not in self.city:
                self.city = self.city + '_(город)'
                self.get_wiki_html()
            else:
                self.url_wiki = ''
                self.latitude = None
                self.longitude = None
                return False
        else:
            self.wiki_html = wiki_html
            return True

    def get_yandex_crumbs(self):
        url = 'https://yandex.by/pogoda?lat={0}&lon={1}'.format(
            self.latitude, self.longitude
        )
        print(url)
        ua = {
            'User-Agent': ('Mozilla/5.0 (Macintosh; '
                           'Intel Mac OS X 10_8_2) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/27.0.1453.116 '
                           'Safari/537.36')
        }
        result = requests.get(url, headers=ua)
        self.html = BeautifulSoup(
            result.text, features="html.parser"
        )
        info = self.html.find_all('span')
        crumbs = [
            item.text for item in info if 'class="breadcrumbs__title"' in str(
                item
            )
        ]
        self.crumbs = ''
        for item in crumbs:
            self.crumbs += '{0}{1}'.format(' > ', item)
        self.crumbs = self.crumbs[3:]

    def get_wiki_descr(self):
        wiki_html = self.wiki_html
        city_desc_array = wiki_html.find_all('p')[:5]
        try:
            city_description = [
                item.text for item in city_desc_array if compare(
                    self.city, item.text
                )
            ][0]
        except IndexError:
            city_description = ''
        try:
            city_description_sec_paragraph = [
                item.text for item in city_desc_array if compare(
                    self.city, item.text
                )
            ][1]
        except IndexError:
            city_description_sec_paragraph = ''
        if len(city_description) < 1000 and city_description != '':
            city_description = (
                city_description + city_description_sec_paragraph
            )
        self.wiki_descr = '{0}{1}{2}{3}'.format(
            city_description[:-1],
            '\n',
            '\t' * 16,
            '(из википедии)\n'
        ) if city_description != '' else ''

    def get_coordinates_wiki(self):
        wiki_html = self.wiki_html
        coord_start = str(wiki_html).find(
            '"wgCoordinates":{'
        ) + len('"wgCoordinates":{')
        coord_end = str(wiki_html)[coord_start:].find('}') + coord_start
        coordinates = str(wiki_html)[coord_start:coord_end]
        self.latitude = coordinates[6:coordinates.find(',')].replace(':', '')
        self.longitude = (coordinates[coordinates.find(
            ','
        ) + 7:coordinates.find(',') + 7 + 15])

    def find_in_list(self):
        cities = cities_id.cities()
        for c in cities:
            if self.init_city.lower() in c.lower():
                city_id = cities[c]
                return city_id

    def get_coordinates_dateandtime(self):
        cities = cities_id.cities()
        try:
            city_id = cities[self.init_city]
        except KeyError:
            return False
        url = 'https://dateandtime.info/ru/citycoordinates.php?id=' + city_id
        ua = {
            'User-Agent': ('Mozilla/5.0 (Macintosh; '
                           'Intel Mac OS X 10_8_2) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/27.0.1453.116 '
                           'Safari/537.36')
        }
        result = requests.get(url, headers=ua)
        self.html = BeautifulSoup(
            result.text, features="html.parser"
        )
        cent_degrees = str(self.html).find(
            'десятичных градусах</h2>'
        ) + len('десятичных градусах</h2>')
        coord = str(self.html)[cent_degrees:cent_degrees + 100]
        latitude_start = coord.find('Широта:') + len('Широта:')
        latitude_end = latitude_start + 12
        lon_start = coord.find('Долгота:') + len('Долгота:')
        lon_end = lon_start + 12

        latitude = coord[latitude_start:latitude_end].replace(' ', '')[:9]
        longitude = coord[lon_start:lon_end].replace(' ', '')[:9]
        try:
            f_latitude = float(latitude)
            f_longitude = float(longitude)
        except ValueError:
            return False
        else:
            self.latitude = latitude
            self.longitude = longitude
            return True


class Weather():

    def __init__(self, city, api):
        self.api = api
        self.is_result = True
        self.wrong_api = False
        self.latitude = city.latitude
        self.longitude = city.longitude
        self.wiki_descr = city.wiki_descr
        self.crumbs = city.crumbs
        self.url = '{0}{1}{2}{3}{4}'.format(
            'https://api.weather.yandex.ru/v1/forecast?lat=',
            self.latitude,
            '&lon=',
            self.longitude,
            '&extra=true'
        )
        self.url_wiki = city.url_wiki

    def send_request(self):
        ua_key = {
            'X-Yandex-API-Key': self.api
        }
        self.result = requests.get(self.url, headers=ua_key).text

    def get_json(self):
        self.json_str = self.result

    @staticmethod
    def get_prec(self):
        pass

    @staticmethod
    def get_cloudness(self):
        pass

    @staticmethod
    def get_prec_strength(self):
        pass

    @staticmethod
    def get_condition(cond_code):
        conditions = {
            'clear': 'Ясно',
            'partly-cloudy': 'Малооблачно',
            'cloudy': 'Облачно с прояснениями',
            'overcast': 'Пасмурно',
            'partly-cloudy-and-light-rain': 'Небольшой дождь',
            'partly-cloudy-and-rain': 'Дождь',
            'overcast-and-rain': 'Сильный дождь',
            'overcast-thunderstorms-with-rain': 'Сильный дождь, гроза',
            'cloudy-and-light-rain': 'Небольшой дождь',
            'overcast-and-light-rain': 'Небольшой дождь',
            'cloudy-and-rain': 'Дождь',
            'overcast-and-wet-snow': 'Дождь со снегом',
            'partly-cloudy-and-light-snow': 'Небольшой снег',
            'partly-cloudy-and-snow': 'Снег',
            'overcast-and-snow': 'Снегопад',
            'cloudy-and-light-snow': 'Небольшой снег',
            'overcast-and-light-snow': 'Небольшой снег',
            'cloudy-and-snow': 'Снег',
        }
        return(conditions[cond_code])

    @staticmethod
    def get_wind_direct(wind_direct_code):
        directions = {
            'nw': 'северо-западный',
            'n': 'северный',
            'ne': 'северо-восточный',
            'e': 'восточный',
            'se': 'юго-восточный',
            's': 'южный',
            'sw': 'юго-западный',
            'w': 'западный',
            'с': 'штиль'
        }
        return(directions[wind_direct_code])

    def json_parce_now(self):
        self.parsed_string = json.loads(self.json_str)
        try:
            if self.parsed_string['status'] == 403:
                self.wrong_api = True
                self.check_api_message = ('!!!              Please check '
                                          'your Yandex API Key'
                                          '              !!!')
                self.is_result = False
                return 'wrong api'
        except KeyError:
            pass
        text_header = '\n\n' + self.crumbs + '\n\n'
        text_descr = self.wiki_descr + '\n'
        text_url_yandex = 'Yandex:     ' + self.parsed_string[
            'info'
        ]['url'] + '\n'
        text_url_wiki = 'Wiki:           ' + self.url_wiki + '\n\n'
        text_now_header = ('\n\t\tПогода сейчас: \n\n')
        text_condition = self.get_condition(
            self.parsed_string['fact']['condition']) + '\n'
        text_temp = '{0}{1}{2}{3}'.format(
            'Температура воздуха ', self.parsed_string[
                'fact'
            ]['temp'], '*C', '\n'
        )
        text_feel_like = '{0}{1}{2}{3}'.format(
            'Ощущается как ', self.parsed_string[
                'fact'
            ]['feels_like'],
            '*C',
            '\n'
        )
        try:
            text_water = '{0}{1}{2}{3}'.format(
                'Температура воды ', self.parsed_string[
                    'fact'
                ]['temp_water'], '*C',
                '\n'
            )
        except KeyError:
            text_water = ''
        text_wind = '{0}{1}{2}{3}{4}{5}{6}{7}'.format(
            'Ветер ',
            str(self.get_wind_direct(self.parsed_string[
                'fact'
            ]['wind_dir'])),
            ', скорость ',
            self.parsed_string[
                'fact'
            ]['wind_speed'],
            ' м/с, порывы до ',
            self.parsed_string[
                'fact'
            ]['wind_gust'],
            ' м/с',
            '\n'
        )
        text_pressure = '{0}{1}{2}{3}'.format(
            'Атмосферное давление ',
            self.parsed_string[
                'fact'
            ]['pressure_mm'],
            ' мм. рт. ст.',
            '\n'
        )
        text_humidity = '{0}{1}{2}{3}'.format(
            'Относительная влажность ',
            str(self.parsed_string[
                'fact'
            ]['humidity']),
            '%',
            '\n'
        )

        full_text = '{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10} {11}'.format(
            text_header,
            text_descr,
            text_url_yandex,
            text_url_wiki,
            text_now_header,
            text_condition,
            text_temp,
            text_feel_like,
            text_water,
            text_wind,
            text_pressure,
            text_humidity
        )
        return full_text

    def json_parce_fore(self):
        if not self.is_result:
            return 'wrong api'
        self.parsed_string = json.loads(self.json_str)
        part = ['morning', 'day', 'evening', 'night']
        head = ['утро', 'день', 'вечер', 'ночь']
        full_text = '\t\tПрогноз на сегодня:\n'
        for p, h in zip(part, head):
            text_space = '{0}{1}{2}'.format('\n\t\t', h, '\n')
            text_cond = '{0}{1}'.format(
                self.get_condition(self.parsed_string[
                    'forecasts'
                ][0]['parts'][p]['condition']),
                '\n'
            )
            text_temp = '{0}{1}{2}{3}'.format(
                'Температура воздуха ',
                self.parsed_string[
                    'forecasts'
                ][0]['parts'][p]['temp_avg'],
                '*C',
                '\n'
            )
            text_feel_like = '{0}{1}{2}{3}'.format(
                'Ощущается как ',
                self.parsed_string[
                    'forecasts'
                ][0]['parts'][p]['feels_like'],
                '*C',
                '\n'
            )
            try:
                text_water = '{0}{1}{2}{3}'.format(
                    'Температура воды ',
                    self.parsed_string[
                        'forecasts'
                    ][0]['parts'][p]['temp_water'],
                    '*C',
                    '\n'
                )
            except KeyError:
                text_water = ''
            text_wind = '{0}{1}{2}{3}{4}{5}{6}{7}'.format(
                'Ветер ',
                str(self.get_wind_direct(self.parsed_string[
                    'forecasts'
                ][0]['parts'][p]['wind_dir'])),
                ', скорость ',
                self.parsed_string[
                    'forecasts'
                ][0]['parts'][p][
                    'wind_speed'
                ],
                ' м/с, порывы до ',
                self.parsed_string[
                    'forecasts'
                ][0]['parts'][p]['wind_gust'],
                ' м/с',
                '\n'
            )
            text_pressure = '{0}{1}{2}{3}'.format(
                'Атмосферное давление ',
                self.parsed_string[
                    'forecasts'
                ][0]['parts'][p]['pressure_mm'],
                ' мм. рт. ст.',
                '\n'
            )
            text_humidity = '{0}{1}{2}{3}'.format(
                'Относительная влажность ',
                str(self.parsed_string[
                    'forecasts'
                ][0]['parts'][p]['humidity']),
                '%',
                '\n'
            )
            part_text = '{0} {1} {2} {3} {4} {5} {6} {7}'.format(
                text_space,
                text_cond,
                text_temp,
                text_feel_like,
                text_water,
                text_wind,
                text_pressure,
                text_humidity
            )
            full_text = full_text + part_text
        return full_text


if __name__ == '__main__':

    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
