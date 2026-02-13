from xml.etree import ElementTree as ET
import sys
sys.path.insert(0, 'migration')
from xml_mappers import clean_wysiwyg_content

test_cases = [
    'https://www.sarahlawrence.edu/graduate/',
    'https://www.sarahlawrence.edu/',
    'https://www.sarahlawrence.edu/global-education/',
    'https://www.sarahlawrence.edu/faculty/index.xml',
    'https://www.sarahlawrence.edu/undergraduate/index.xml',
]

for url in test_cases:
    wysiwyg = ET.fromstring(f'<wysiwyg><a href="{url}">Test</a></wysiwyg>')
    clean_wysiwyg_content(wysiwyg)
    result = wysiwyg.find('a').get('href')
    print(f"{url:60s} -> {result}")
