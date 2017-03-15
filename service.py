# -*- coding: utf-8 -*-
'''
    Author    : Huseyin BIYIK <husenbiyik at hotmail>
    Year      : 2016
    License   : GPL

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import sublib

import re
import os

domain = "http://www.turkcealtyazi.org"

quals = {
         "1": 5,  # good quality
         "2": 4,  # enough quality
         "3": 0,  # bad quality
         "4": 2,  # not rated yet
         "5": 1,  # waiting for source
         "6": 3,  # archived
         }


def norm(txt):
    txt = txt.replace(" ", "")
    txt = txt.lower()
    return txt


def striphtml(txt):
    txt = re.sub("<.*?>", "", txt)
    txt = re.sub("\t", "", txt)
    txt = re.sub("\n", "", txt)
    txt = txt.replace("  ", " ")
    return txt


class turkcealtyazi(sublib.service):

    def search(self):
        self.found = False
        if self.item.imdb:
            self.find(self.item.imdb)
        if not self.num() and not self.item.show and self.item.year:
            self.find("%s %s" % (self.item.title, self.item.year))
        self._subs = []
        if not self.num():
            self.find(self.item.title)

    def checkpriority(self, txt):
        # this is a very complicated and fuzzy string work
        txt = txt.lower().replace(" ", "")
        cd = re.search("([0-9])cd", txt)
        # less the number of cds higher the priority
        if cd:
            return False, - int(cd.group(1))
        # rest is for episodes, if movie then return lowest prio.
        if self.item.episode < 0 or not self.item.show:
            return False, -100
        ispack = 0
        packmatch = 0
        epmatch = 0
        skip = False
        se = re.search("s(.+?)\|e(.+)", txt)
        if not se:
            se = re.search("s(.+?)(paket)", txt)
        if se:
            e = se.group(2)
            s = se.group(1)
            # verify season match first
            if s.isdigit() and self.item.season > 0 and \
                    not self.item.season == int(s):
                return True, 0
            ismultiple = False
            # e: 1,2,3,4 ...
            for m in e.split(","):
                if m.strip().isdigit():
                    ismultiple = True
                else:
                    ismultiple = False
                    break
            if ismultiple:
                # check if in range
                multiples = [int(x) for x in e.split(",")]
                if self.item.episode in multiples:
                    packmatch = 2
                else:
                    skip = True
            # e: 1~4
            if "~" in e:
                startend = e.split("~")
                # check if in range
                if len(startend) == 2 and \
                    startend[0].strip().isdigit() and \
                        startend[1].strip().isdigit():
                    if int(startend[0]) < self.item.episode and \
                            int(startend[1]) > self.item.episode:
                        packmatch = 2
                    else:
                        skip = True
                else:
                    ispack = 1
            # e: Paket meaning a package
            if e == "paket":
                ispack = 1
            # e:1 or e:01
            if e.isdigit():
                if int(e) == self.item.episode:
                    epmatch = 3
                else:
                    skip = True
        return skip, ispack + epmatch + packmatch

    def scraperesults(self, page, query=None):
        match = re.findall('<a href="(.+?)" title="(.+?)".*?><span style="font-size:15px"><strong>.+?<span style="font-size:15px">\(([0-9]{4})\)', page)
        for link, name, year in match:
            year = int(year)
            if norm(name) == norm(self.item.title) and \
                (self.item.show or
                    (self.item.year is None or self.item.year == year)):
                self.found = True
                self.scrapepage(self.request(domain + link))
                break
        if query and not self.found:
            pages = re.findall('<a href="/find\.php.*?">([0-9]+?)</a>', page)
            if len(pages):
                for p in range(2, int(pages[-1]) + 1):
                    if self.found:
                        break
                    query["p"] = p
                    self.scraperesults(self.request(domain + "/find.php", query))

    def scrapepage(self, page):
        subs = re.findall('<div class="altsonsez(.+?)</div>\s+?</div>\s+?<div>', page, re.DOTALL)
        for s in subs:
            r_name = re.search('<a itemprop="url" class="underline".+?href="(.+?)".+?<strong>(.+?)<\/strong>', s)
            link = r_name.group(1)
            name = r_name.group(2)
            r_desc = re.search('<div class="alcd">(.+?)<\/div>', s, re.DOTALL)
            desc = striphtml(r_desc.group(1))
            skip, priority = self.checkpriority(desc)
            if skip:
                continue
            r_tran = re.search('<div class="alcevirmen">(.+?)<\/div>', s, re.DOTALL)
            tran = striphtml(r_tran.group(1))
            r_rel = re.search('<div class="alrelease">(.+?)<\/div>', s, re.DOTALL)
            rel = striphtml(r_rel.group(1))
            r_iso = re.search('<span class="flag([a-z]{2})">', s)
            iso = r_iso.group(1)
            namestr = "%s, %s, %s, %s" % (name, desc, rel, tran)
            qual = re.search('<span class="kal([0-9])"', s)
            sub = self.sub(namestr, iso)
            sub.download(domain + link)
            sub.priority = priority
            if qual:
                sub.rating = quals[qual.group(1)]
            self.addsub(sub)

    def find(self, query):
        q = {"cat": "sub", "find": query}
        page = self.request(domain + "/find.php", q)
        title = re.search("<title>(.*?)</title>", page)
        if "arama" in title.group(1):
            self.scraperesults(page, q)
        else:
            self.scrapepage(page)

    def download(self, link):
        page = self.request(link)
        idid = re.search('<input type="hidden" name="idid" value="(.+?)"',
                                                                        page)
        alid = re.search('<input type="hidden" name="altid" value="(.+?)"',
                                                                        page)
        sdid = re.search('<input type="hidden" name="sidid" value="(.+?)"',
                                                                        page)
        data = {
               "idid": idid.group(1),
               "altid": alid.group(1),
               "sidid": sdid.group(1)
               }
        remfile = self.request(domain + "/down.php", None, data, domain, True)
        fname = remfile.info().getheader("Content-Disposition")
        fname = re.search('filename=(.*)', fname)
        fname = fname.group(1)
        fname = os.path.join(self.path, fname)
        with open(fname, "wb") as f:
            f.write(remfile.read())
        self.addfile(fname)
