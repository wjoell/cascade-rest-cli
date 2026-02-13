from xml.etree import ElementTree as ET
import sys
sys.path.insert(0, 'migration')
from xml_mappers import clean_wysiwyg_content

# Create test element
wysiwyg = ET.fromstring('<wysiwyg><p><a href="https://www.sarahlawrence.edu/faculty/index.xml">Test</a></p></wysiwyg>')
print("Before:", ET.tostring(wysiwyg, encoding='unicode'))
clean_wysiwyg_content(wysiwyg)
print("After:", ET.tostring(wysiwyg, encoding='unicode'))
