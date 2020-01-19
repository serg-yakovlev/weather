import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class CitiesTree(Gtk.TreeView):

    def __init__(self, cities):
        self.store = Gtk.ListStore(str)
        for city in cities:
            self.store.append([city])
        super().__init__(model=self.store.filter_new())
        self.set_size_request(200, 200)
        column_names = ['City']
        for i, col_n in enumerate(column_names):
            column = Gtk.TreeViewColumn(col_n, Gtk.CellRendererText(), text=i)
            column.set_resizable(True)
            self.append_column(column)

    def fill_store(self, cities):
        self.store.clear()
        i = 0
        for city in cities:
            self.store.append([city])
            i += 1
        self.city_counter = i
        self.selected_city = city if i == 1 else None


if __name__ == '__main__':
    w = Gtk.Window(title='Cities')
    t = CitiesTree(['Минск', 'Вильнюс', 'Киев', 'Москва', 'Одесса'])
    w.set_size_request(1000, 500)
    master_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    w.add(master_box)
    scrollable_treelist = Gtk.ScrolledWindow()
    scrollable_treelist.set_size_request(570, 470)
    master_box.add(scrollable_treelist)
    scrollable_treelist.add(t)
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
