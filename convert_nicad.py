import xml.etree.ElementTree as ET
import pathlib
import sys

class codeblock:
    def __init__(self, fn: str, begin: int, end: int):
        self.fn = fn
        self.begin = begin
        self.end = end
    
    @classmethod
    def by_xml(cls, elem):
        path = pathlib.PurePath(elem.attrib['file'])
        dir = path.parent.name
        name = path.name
        begin = int(elem.attrib['startline'])
        end = int(elem.attrib['endline'])
        return codeblock(f'{dir},{name}', begin, end)
    
    def __repr__(self):
        return f'{self.fn},{self.begin},{self.end}'

class clonepair:
    def __init__(self, cb1: codeblock, cb2: codeblock):
        self.b1 = cb1
        self.b2 = cb2
        if self.b1.fn < self.b2.fn:
            self.b1, self.b2 = self.b2, self.b1
    
    @classmethod
    def by_xml(cls, elem):
        cb1 = codeblock.by_xml(elem[0])
        cb2 = codeblock.by_xml(elem[1])
        return clonepair(cb1, cb2)
    
    def __repr__(self):
        return f'{self.b1.__repr__()},{self.b2.__repr__()}'

ifn = sys.argv[1]
ofn = sys.argv[2]

tree = ET.parse(ifn)
root = tree.getroot()
with open(ofn, "w") as f:
    for child in root:
        if child.tag != 'clone':
            continue
        cp = clonepair.by_xml(child)
        f.write(cp.__repr__() + '\n')