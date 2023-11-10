import urllib.request
import datetime

from bs4 import BeautifulSoup
from pyopenmensa.feed import LazyBuilder

def _remove_multiple_whitespaces(s: str):
    return ' '.join(s.split()).strip()

def parse_mensa_plan(url: str):
    canteen = LazyBuilder()
    
    # updates canteen with data of current week
    # the data of the current week is necessary
    # thus, if an error occurs, parsing for this mensa is cancelled (by propagating the error)
    canteen = update_canteen(canteen, url)
    
    # try to get canteen data for next week
    # data for the next week is available by appending 'nächste-woche' to the url
    # The 'ä' in this appendix needs to be escaped as '%c3%a4'
    # if an error occurs during parsing, the program will continue without next weeks data
    if url[-1] != '/':
        url += '/'
    next_week_url = url
    next_week_url += 'n%c3%a4chste-woche/'
    try:
        canteen = update_canteen(canteen, next_week_url)
    except Exception as e:
        print(f'Could not load next week data for {url}')
        print(f'Exception: {e}')
    
    return canteen.toXMLFeed()

def update_canteen(canteen, url: str):
    soup = None
    with urllib.request.urlopen(url) as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    if soup is None:
        raise Exception(f'Could not read from url {url}')
    
    menuDays = soup.find_all('div', class_='menuDay')
    
    for menuDay in menuDays:
        # dates are formatted as YYYYMMDD, eg 20230401 for April 1st 2023
        date_string = menuDay['data-selector']
        date = datetime.datetime.strptime(date_string, '%Y%m%d').date()
        menuItems = menuDay.find_all('div', class_='menuItem')
        for menuItem in menuItems:
            # Extract the name of the meal from the menu items headline
            name = menuItem.find('h3', class_='menuItem__headline').string
            name = _remove_multiple_whitespaces(name)
            
            # Extract the prices for the three different groups students, employees, guests (others)
            prices = {}
            price_1 = menuItem.find('p', class_='menuItem__price__one')
            if price_1 is not None:
                prices['student'] = _remove_multiple_whitespaces(price_1.find('span', type='button').string)
            price_2 = menuItem.find('p', class_='menuItem__price__two')
            if price_2 is not None:
                prices['employee'] = _remove_multiple_whitespaces(price_2.find('span', type='button').string)
            price_3 = menuItem.find('p', class_='menuItem__price__three')
            if price_3 is not None:
                prices['other'] = _remove_multiple_whitespaces(price_3.find('span', type='button').string)
            
            # Create an empty list for notes
            notes = []
            
            # Sidedishes use a different structure and need to be handled differently from other menu items
            if 'menuItem--sidedish' in menuItem['class']:
                # The category of a sidedish is stored in the headline, which usually stores the name of main dishes
                category = name
                # The name of each sidedish is stored in each sidedish label
                for label in menuItem.find_all('strong', class_='menuItem__sidedish__label'):
                    name = _remove_multiple_whitespaces(label.string)
                    canteen.addMeal(date, category, name, prices=prices, notes=notes)
            else:
                category = menuItem.find('span', class_='menuItem__line').string.strip()
                menuItemText = menuItem.find('p', class_='menuItem__text').string
                if menuItemText is not None:
                    # Some menu items might have an empty text
                    notes += [ _remove_multiple_whitespaces(menuItemText) ]
                canteen.addMeal(date, category, name, prices=prices, notes=notes)
        
    return canteen

if __name__ == '__main__':
    # For debug purposes do parsing for Bielefeld Mensa X
    xml_feed = parse_mensa_plan('https://www.studierendenwerk-bielefeld.de/essen-trinken/speiseplan/bielefeld/mensa-x/')
    print(xml_feed)

