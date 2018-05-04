# -*- coding: utf-8 -*-
import django
django.setup()

import json
from collections import defaultdict
from sefaria.model import *
from pprint import pprint


class Play(object):
    def __init__(self, name):
        self.name = name
        self.acts = []
        self.current_act = 0

    def __str__(self):
        return self.name

    def add_act(self, first_line):
        n = Act(first_line)
        self.acts += [n]
        self.current_act = len(self.acts)
        return n


class Act(object):
    def __init__(self, first_line):
        self.scenes = []
        self.current_scene = 0
        self.first_line = first_line

    def __str__(self):
        return self.first_line.text

    def add_scene(self, first_scene_line):
        if self.current_scene == 0:
            n = Scene([self.first_line, first_scene_line])
        else:
            n = Scene([first_scene_line])
        self.scenes += [n]
        self.current_scene = len(self.scenes)
        return n


class Scene(object):
    def __init__(self, first_lines):
        self.lines = first_lines
        self.first_line = first_lines[-1]

    def __str__(self):
        return self.first_line.text

    def add_line(self, line):
        self.lines += [line]

    def array(self):
        # set blank array to maximum size
        result = [""] * len(self.lines)

        i = 0
        accumlator = ""

        while i < len(self.lines):
            line = self.lines[i]

            if not line.line_num:
                accumlator += line.complete_text() + "<br>"
                i += 1
                continue
            else:
                t = accumlator + line.complete_text()
                num = line.line_num - 1
                accumlator = ""

            try:
                while line.nxt and not line.nxt.num and line.speech_num == line.nxt.speech_num:
                    t += "<br>" + line.nxt.complete_text()
                    line = line.nxt
                    i += 1
            except AttributeError as e:
                pass

            if num >= len(result):
                print "Error {}/{}: {}".format(num,len(result),t)
            result[num] = t
            i += 1

        # trim off end of array
        while result[-1] == "":
            result.pop()

        return result


class Line(object):
    def __init__(self, type, id, num, speaker, speech_num, text):
        self.type = type
        self.id = id
        self.num = num if "." in num else None
        self.derive_numbers()
        self.speech_num = speech_num
        self.text = text
        self.speaker = speaker
        self.prev = None
        self.nxt = None

    def derive_numbers(self):
        self.line_num = None
        self.act_num = None
        self.scene_num = None
        if self.num:
            self.act_num, self.scene_num, self.line_num = map(int, self.num.split("."))

    def __str__(self):
        return "{} {}".format(self.num, self.text)

    def __repr__(self):
        return str(self)

    def set_previous_line(self, prev):
        self.prev = prev
        if prev:
            prev.nxt = self

    def matches_previous_speaker(self):
        return self.prev and self.speaker == self.prev.speaker

    def complete_text(self):
        txt = "<em>{}</em><br>".format(self.text) if self.type == "line" and not self.num else self.text
        if self.type in ["act", "scene"]:
            return "&emsp;&emsp;&emsp;&emsp;{}".format(txt)
        if not self.speaker or self.matches_previous_speaker():
            return "&emsp;" + txt
        else:
            return "{}<br>&emsp;{}".format(self.speaker, txt)

# line_id
# line_number
# play_name
# speaker
# speech_number
# text_entry
# type  -  u'act', u'line', u'scene'

plays = {}
data = json.load(open('shakespeare_6.0.json'))


prev_number = None
for d in data:
    if d["line_number"] == prev_number:
        d["line_number"] = ""
    else:
        prev_number = d["line_number"]

play = None
act = None
scene = None
prev_line = None

for d in data:
    if d["play_name"] in ["Henry V", "Henry VIII", "Pericles", "Taming of the Shrew", "Merchant of Venice", "Romeo and Juliet", "Troilus and Cressida"]:
        continue  # "Henry V", "Henry VIII", "Pericles", "Taming of the Shrew", RAJ, TAC have lines outside of a scene, or scenes outside acts.
                  # MOV has bad data - Act I, Scene II is misnumbered
    try:
        play = plays[d["play_name"]]
    except KeyError:
        play = Play(d["play_name"])
        plays[d["play_name"]] = play
        act = None
        scene = None
        prev_line = None

    line = Line(d["type"], d["line_id"], d["line_number"], d["speaker"], d["speech_number"], d["text_entry"])

    try:
        type = d["type"]
        if type == "act":
            prev_line = None
            act = play.add_act(line)
        elif type == "scene":
            scene = act.add_scene(line)
        elif type == "line":
            scene.add_line(line)

        line.set_previous_line(prev_line)
        prev_line = line
    except Exception as e:
        print vars(line)
        print e

for name, play in plays.iteritems():
    hname = u"א" + name
    index = Index()
    index.set_title(name)
    index.categories = ["Drama", "Shakespeare"]

    '''
    root = JaggedArrayNode()
    root.add_primary_titles(name, hname)
    root.add_structure(["Act"])
    root.index = index

    for act in play.acts:
        act_node = JaggedArrayNode()
        title = act.first_line.text.replace("-", " ").replace(".", " ").strip()
        act_node.add_primary_titles(title, u"א" + title)
        act_node.add_structure(["Scene"])
        act_node.index = index
        root.append(act_node)
        for scene in act.scenes:
            scene_node = JaggedArrayNode()
            title = scene.first_line.text.replace("-", " ").replace(".", " ").strip()
            scene_node.add_primary_titles(title, u"א" + title)
            scene_node.add_structure(["Line"])
            scene_node.index = index
            act_node.append(scene_node)
    '''
    root = JaggedArrayNode()
    root.add_primary_titles(name, hname)
    root.add_structure(["Act", "Scene", "Line"])
    root.index = index

    index.nodes = root

    IndexSet({"title":name}).delete()

    try:
        index.save()
    except Exception:
        pass

    data = [[scene.array() for scene in act.scenes] for act in play.acts]

    VersionSet({"title":name}).delete()
    v = Version()
    v.versionTitle = "Elastic Search"
    v.versionSource = "https://www.elastic.co/guide/en/kibana/current/tutorial-load-dataset.html"
    v.language = "en"
    v.chapter = data
    v.title = name
    v.save()
