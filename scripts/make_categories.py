# -*- coding: utf-8 -*-
import django
django.setup()

from sefaria.model import *
from sefaria.system.database import db


def create_category(en, he, parent=None):
    parent_path = parent.path if parent else []

    t = Term()
    t.add_primary_titles(en, he)
    t.scheme = "toc_categories"
    t.name = en
    t.save()

    c = Category()
    # if Term().load({"name": treenode.primary_title("en")}):
    #    c.add_shared_term(treenode.primary_title("en"))
    c.add_primary_titles(en, he)
    c.path = parent_path + [en]
    c.lastPath = en
    print "Creating - {}".format(" / ".join(c.path))
    c.save(override_dependencies=True)
    return c

db.category.remove({})
db.term.remove({})

for s in ["Act","Scene","Line","Book","Page","Paragraph"]:
    t = Term()
    t.name = s
    t.add_primary_titles(s, u"א" + s)
    t.scheme = "section_names"
    t.save()

poetry = create_category("Poetry", u"שירה")
prose = create_category("Fiction", u"פרוזה")
nonfiction = create_category("Non Fiction", u"לא בדיוני")
drama = create_category("Drama", u"דרמה")
folklore = create_category("Folklore", u"פולקלור")
philosophy = create_category("Philosophy", u"א")
religious_texts = create_category("Religious Texts", u"ב")

create_category("Shakespeare", u"שייקספיר", drama)
cphil = create_category("Classical Philosophy", u"ג", philosophy)
plato = create_category("Plato", u"ד", cphil)
