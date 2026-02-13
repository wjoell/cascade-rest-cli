from xml.etree import ElementTree as ET
import copy

# Create and modify
wysiwyg = ET.fromstring('<wysiwyg><p><a href="https://www.sarahlawrence.edu/faculty/index.xml">Test</a></p></wysiwyg>')
print("Original:", ET.tostring(wysiwyg, encoding='unicode'))

# Modify the link
for a in wysiwyg.iter('a'):
    a.set('href', '/faculty/index')
print("Modified:", ET.tostring(wysiwyg, encoding='unicode'))

# Deep copy
wysiwyg2 = ET.Element('wysiwyg')
for child in wysiwyg:
    wysiwyg2.append(copy.deepcopy(child))
print("After deepcopy:", ET.tostring(wysiwyg2, encoding='unicode'))
