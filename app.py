import requests
import json
import cities_id
from bs4 import BeautifulSoup
from cities_tree import CitiesTree
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class MainWindow(Gtk.Window):

    def __init__(self):
        super().__init__(title="Weather forecast from Yandex")
        self.connection = None
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_size_request(1000, 500)
        master_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(master_box)
        hpaned = Gtk.Paned()
        master_box.add(hpaned)
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        search_header = Gtk.Label(label='SEARCH CITY')
        self.forecast_header = Gtk.Label(label='WEATHER FORECAST')
        left_box.pack_start(search_header, False, True, 0)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.search_entry = Gtk.Entry()
        search_box.pack_start(self.search_entry, False, True, 0)
        search_button = Gtk.Button(label="Search")
        search_button.connect('clicked', self.set_forecast_wiki)
        search_box.pack_start(search_button, False, True, 0)
        self.search_entry.connect('changed', self.entry_changed)
        left_box.pack_start(search_box, False, True, 0)
        right_box.pack_start(self.forecast_header, False, True, 0)
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
        self.weather_info_label.set_size_request(430, 210)
        self.weather_info_label.set_selectable(True)
        self.weather_info_label.set_line_wrap(True)
        right_box.pack_start(self.weather_info_label, True, True, 0)
        self.selection_block = False

    def entry_changed(self, entry):
        # if entry.get_text() == '':
        #    self.weather_info_label.set_text(
        #        ''
        #    )
        self.selection_block = True
        selected_cities = []
        for city in self.cities:
            if entry.get_text().lower() in city.lower():
                selected_cities.append(city)
        self.cities_treeview.fill_store(selected_cities)

        if self.cities_treeview.selected_city:
            self.set_forecast_text(self.cities_treeview.selected_city)
        else:
            self.weather_info_label.set_text(
                ''
            )
        self.selection_block = False
        # if self.cities_treeview.city_counter == 0:
        #    try:
        #        self.set_forecast_text(entry.get_text())
        #    except Exception:
        #        pass

    def set_forecast_text(self, city):
        self.weather_info_label.set_text(
            'Получение данных, прогноз сформируется через несколько секунд'
        )
        c = City(city)
        c.get_coordinates(city)
        if (not c.long) or (not c.lat):
            c.get_coordinates_dateandtime(city)
        if (not c.long) or (not c.lat):
            self.weather_info_label.set_text(
                'Проверьте введенное название города'
            )
        else:
            long = c.long
            lat = c.lat
        w = Weather(lat, long)
        w.send_request()
        w.get_json()
        forecast = w.json_parce_now() + ('\n\n') + w.json_parce_fore()
        if w.wrong_api:
            self.weather_info_label.set_text(w.check_api_message)
        else:
            self.weather_info_label.set_text(forecast)
        w.get_city_info()

    def set_forecast_wiki(self, button):
        city = self.search_entry.get_text()
        self.set_forecast_text(city)

    def set_forecast_for_selection(self, selection):
        if not self.selection_block:
            model, treeiter = selection.get_selected()
            city = model[treeiter][0]
            self.set_forecast_text(city)


class City():

    def __init__(self, city):
        self.city = city

    def get_city_url(self):
        url = 'https://dateandtime.info/ru/citycoordinates.php?id='
        # city = input("Город (часть названия): ")
        cities = cities_id.cities()
        for c in cities:
            if self.city.lower() in c.lower():
                city_url = url + cities[c]
                self.city_id = cities[c]
                print(c, city_url)
                return(city_url)
        return 'no result'

    def get_coordinates(self, city_full_name):
        city_full_name = city_full_name.title().replace('Город', 'город')
        print(city_full_name)
        ua = {
            'User-Agent': ('Mozilla/5.0 (Macintosh; '
                           'Intel Mac OS X 10_8_2) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/27.0.1453.116 '
                           'Safari/537.36')
        }
        url = 'https://ru.wikipedia.org/wiki/' + city_full_name + '#/maplink/0'
        print(url)
        result = requests.get(url, headers=ua)
        self.html = BeautifulSoup(
            result.text, features="html.parser"
        )
        # print(self.html)
        coord_start = str(self.html).find(
            '"wgCoordinates":{'
        ) + len('"wgCoordinates":{')
        coord_end = str(self.html)[coord_start:].find('}') + coord_start
        coordinates = str(self.html)[coord_start:coord_end]
        print(coordinates)
        lat = coordinates[6:coordinates.find(',')].replace(':', '')
        long = (coordinates[coordinates.find(
            ','
        ) + 7:coordinates.find(',') + 7 + 15])
        print('!!!!', lat, 'and!!!!!!!!!!', long)
        try:
            f_lat = float(lat)
            f_lon = float(long)
        except ValueError:
            if '_(город)' not in city_full_name:
                self.get_coordinates(city_full_name + '_(город)')
            else:
                self.lat = None
                self.long = None
        else:
            self.lat = lat
            self.long = long

    def get_coordinates_dateandtime(self, city):
        url = self.get_city_url()
        if url == 'no result':
            return
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
        cent_degrees = str(self.html).find(
            'десятичных градусах</h2>'
        ) + len('десятичных градусах</h2>')
        coord = str(self.html)[cent_degrees:cent_degrees + 100]
        print(coord)
        lat_start = coord.find('Широта:') + len('Широта:')
        lat_end = lat_start + 12
        print('/t/t')
        print(coord[lat_start:lat_end])
        print(lat_start)
        print(lat_end)
        lon_start = coord.find('Долгота:') + len('Долгота:')
        lon_end = lon_start + 12

        self.lat = coord[lat_start:lat_end].replace(' ', '')[:9]
        self.long = coord[lon_start:lon_end].replace(' ', '')[:9]


class Weather():

    def __init__(self, lat, long):
        self.url = ('https://api.weather.yandex.ru'
                    '/v1/forecast?lat=') + lat + '&lon=' + long + '&extra=true'
        print(self.url)
        self.is_result = True
        self.wrong_api = False
        self.lat = lat
        self.long = long

    def send_request(self):
        ua_key = {
            'X-Yandex-API-Key': 'fdf02e4b-968d-4edd-9871-279b7086dde5'
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

    def get_city_info(self):
        url = 'https://yandex.by/pogoda?lat={0}&lon={1}'.format(
            self.lat, self.long
        )
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
        return str(crumbs)

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
        text_header = self.get_city_info()
        text_url = ('url',
                    self.parsed_string['info']['url'])
        text_now_header = ('\t\tСейчас: \n')
        text_condition = (self.get_condition(
            self.parsed_string['fact']['condition']))
        text_temp = ('Температура воздуха',
                     self.parsed_string['fact']['temp'], '*C')
        text_feel_like = (
            'Ощущается как', self.parsed_string['fact']['feels_like'], '*C')
        try:
            text_water = (
                'Температура воды', self.parsed_string[
                    'fact'
                ]['temp_water']
            )
        except Exception:
            text_water = ''
        text_wind = ('Ветер', str(self.get_wind_direct(self.parsed_string[
            'fact'
        ]['wind_dir'])) + ', скорость', self.parsed_string[
            'fact'
        ]['wind_speed'], 'м/с, порывы до', self.parsed_string[
            'fact'
        ]['wind_gust'], 'м/с')
        text_pressure = ('Атмосферное давление', self.parsed_string[
            'fact'
        ]['pressure_mm'], 'мм. рт. ст.')
        text_humidity = ('Относительная влажность', str(self.parsed_string[
            'fact'
        ]['humidity']) + '%')

        full_text = '{0} {1} {2} {3} {4} {5} {6} {7} {8} {9}'.format(
            text_header,
            text_url,
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
        full_text = ('\t\tПрогноз:')
        for p, h in zip(part, head):
            text_space = ('\n\t\t', h)
            text_cond = (self.get_condition(self.parsed_string[
                'forecasts'
            ][0]['parts'][p]['condition']))
            # print(self.parsed_string['forecasts'][0]['parts'])
            text_temp = ('Температура воздуха', self.parsed_string[
                'forecasts'
            ][0]['parts'][p]['temp_avg'], '*C')
            text_feel_like = ('Ощущается как', self.parsed_string[
                'forecasts'
            ][0]['parts'][p]['feels_like'], '*C')
            try:
                text_water = ('Температура воды', self.parsed_string[
                    'forecasts'
                ][0]['parts'][p]['temp_water'])
            except Exception:
                text_water = ''
            text_wind = ('Ветер', str(self.get_wind_direct(self.parsed_string[
                'forecasts'
            ][0]['parts'][p]['wind_dir'])) + ', скорость', self.parsed_string[
                'forecasts'
            ][0]['parts'][p][
                'wind_speed'
            ], 'м/с, порывы до', self.parsed_string[
                'forecasts'
            ][0]['parts'][p]['wind_gust'], 'м/с')
            text_pressure = ('Атмосферное давление', self.parsed_string[
                'forecasts'
            ][0]['parts'][p]['pressure_mm'], 'мм. рт. ст.')
            text_humidity = ('Относительная влажность', str(self.parsed_string[
                'forecasts'
            ][0]['parts'][p]['humidity']) + '%')
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

    #    c = City()
    #    c.get_coordinates()
    #    long = c.long
    #    lat = c.lat

    #    w = Weather(lat, long)
    #    w.send_request()
    #    w.get_json()
    #    w.json_parce_now()
    #    print('\n\n')
    #    w.json_parce_fore()

    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
