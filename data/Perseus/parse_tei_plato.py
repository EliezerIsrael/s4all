# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from lxml import etree
import regex
import django
django.setup()
from sefaria.model import *

CLOSING_TAG = "</%s>"
OPENING_TAG = '<%s%s>'
ATTRIBUTE = ' %s="%s"'


class MilestoneSplitter(object):
    """Split files at milestone tag."""
    def __init__(self,
                 milestone_tag,
                 identifying_attr = None,
                 identifying_val = None,
                 ):
        self.milestone_tag = milestone_tag
        self.identifying_attr = identifying_attr
        self.identifying_val = identifying_val
        self.count = 0
        self.parts = []
        self.milestones = []

    def clear_parts(self):
        """Clear the parts dictionary.
        This resets the splitter for the next file."""
        self.parts = []
        self.milestones = []
        self.count = 0

    def split(self, input):
        """Split single file."""
        self.clear_parts()

        # Put the M + 1 textual segments in self.parts[]
        self.split_raw(input)

        # Analyze each Milestone to determine structure
        tree = etree.fromstring(input)
        if self.identifying_attr:
            xpath = './/{}[@{}="{}"]'.format(self.milestone_tag, self.identifying_attr, self.identifying_val)
        else:
            xpath = './/{}'.format(self.milestone_tag)

        # Collect all M milestones in self.milestones[]
        self.milestones = [self.get_parents(m) for m in tree.findall(xpath)]

        # In between parts[x] and parts[x+1] is milestone[x]

        # Add ending tags to all but last one
        for i in range(0, len(self.parts) - 1):
            self.parts[i] = self.parts[i] + u"\n" + self.create_closing_tags(self.milestones[i])

        # Add starting tags to all but first one
        for i in range(1, len(self.parts)):
            self.parts[i] = self.create_opening_tags(self.milestones[i-1]) + u"\n" + self.parts[i]

        return self.parts

    def split_raw(self, text):
        """
            Split the raw text of the file by milestone.
            Returns M+1 Units
        """
        if self.identifying_attr:
            pattern = "<{} [^>]*{}=['\"]{}['\"][^>*]>".format(self.milestone_tag, self.identifying_attr, self.identifying_val)
        else:
            pattern = "<{} [^>*]>".format(self.milestone_tag)
        reg = regex.compile(pattern)

        self.parts = reg.split(text)

    @staticmethod
    def get_parents(milestone):
        """Get the parent tags of the milestone."""
        return [(parent.tag, parent.attrib)
                for parent in milestone.iterancestors()]

    @staticmethod
    def create_closing_tags(parent):
        """Create one closing tag string."""
        closing = ""
        for tag, _ in parent:
            closing += CLOSING_TAG % tag
        return closing

    @staticmethod
    def create_opening_tags(parent):
        """Create one opening tag string."""
        opening = ""
        for tag, pairs in reversed(parent):
            attribute_xml = ""
            for keyvalue in pairs.items():
                attribute_xml += ATTRIBUTE % keyvalue
            attribute_xml += ATTRIBUTE % ("continued", "true")
            opening += OPENING_TAG % (tag, attribute_xml)
        return opening


class Work:
    def __init__(self, tei):
        self._books = []
        self.title = tei.findAll('title')[0].string
        book_tags = tei.findAll("div", subtype="book")
        for b in book_tags:
            book = self.add_book(b)

    def add_book(self, elem):
        b = Book(elem)
        self._books += [b]
        return b

    def array(self):
        return [b.array() for b in self._books]


class Book:
    def __init__(self, elem):
        self._sections = []
        section_tags = elem.findAll("div", subtype="section")
        for section in section_tags:
            self.add_section(section)

    def add_section(self, elem):
        num = int(elem["n"])
        while len(self._sections) < num:
            self._sections += [[]]

        s = Section(elem)
        self._sections[num - 1] = s
        return s

    def array(self):
        return [s.array() if s else [] for s in self._sections]


class Section:
    def __init__(self, elem):
        self._elem = elem
        self._segments = []
        self.transform()

    def transform(self):
        remove_tags = ["said", "p"]
        for tag in remove_tags:
            for e in self._elem(tag):
                e.unwrap()

        for e in self._elem("milestone", unit=["page","section"]):
            e.unwrap()

        for e in self._elem("q"):
            e.insert_before(tei.new_string('"'))
            e.insert_after(tei.new_string('"'))
            e.unwrap()

        for tag in ["gloss","quote","title","foreign","placeName","bibl"]:
            for e in self._elem(tag):
                new_tag = tei.new_tag("i")
                new_tag["class"] = tag
                e.wrap(new_tag)
                e.unwrap()

        for e in self._elem("note"):
            '''
            <sup>1</sup><i class="footnote" style="display: none;"></i>
            '''
            sup = tei.new_tag("sup")
            sup.string = "*"
            e.insert_before(sup)

            new_tag = tei.new_tag("i")
            new_tag["class"] = "footnote"
            new_tag["style"] = "display: none"
            e.wrap(new_tag)
            e.unwrap()

        for seg in msplitter.split(unicode(self._elem)):
            s = "".join([unicode(x) for x in BeautifulSoup(seg, "xml").div.contents]).strip()
            if s:
                self._segments += [s]

    def array(self):
        return self._segments

# <milestone ed="P" unit="para"/>
msplitter = MilestoneSplitter("milestone", "unit", "para")

tei = BeautifulSoup(open("tlg0059.tlg030.perseus-eng2.xml").read(), "xml")
work = Work(tei)

name = "Republic"
hname = u"א" + name
index = Index()
index.set_title(name)
index.categories = ["Philosophy", "Classical Philosophy", "Plato"]

root = JaggedArrayNode()
root.add_primary_titles(name, hname)
root.add_structure(["Book", "Page", "Paragraph"])
root.index = index

index.nodes = root

IndexSet({"title": name}).delete()

try:
    index.save()
except Exception:
    pass


VersionSet({"title": name}).delete()
v = Version()
v.versionTitle = "Perseus"
v.versionSource = ""
v.language = "en"
v.chapter = work.array()
v.title = name
v.save()

'''
To deal with:
<milestone unit="page" resp="Stephanus" n="329"/>
<milestone unit="section" resp="Stephanus" n="329a"/>
<milestone ed="P" unit="para"/>
<p>
<q> for quote
<said> for whom is speaking?  Seems innacurate
<note>
<quote>
<title>
<gloss>
<foreign>
<bibl>
<placeName>
'''

# https://en.wikipedia.org/wiki/Stephanus_pagination
# To begin, we'll just get page numbers. and not column letters.  The latter will need a new address class

