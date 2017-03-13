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
        if not self.num() and self.item.year:
            self.find("%s %s" % (self.item.title, self.item.year))
        if not self.num():
            self.find(self.item.title)

    def scraperesults(self, page, query=None):
        match = re.findall('<a href="(.+?)" title="(.+?)"><span style="font-size:15px"><strong>.+?<span style="font-size:15px">\(([0-9]{4})\)', page)
        print match
        for link, name, year in match:
            year = int(year)
            if norm(name) == norm(self.item.title) and \
                (self.show or
                    (self.item.year is None or self.item.year == year)):
                self.found = True
                self.scrapepage(self.request(link))
        if query and not self.found:
            pages = re.findall('<a href="/find\.php.*?">([0-9]+?)</a>', page)
            if len(pages):
                for p in range(2, int(pages[-1]) + 1):
                    if self.found:
                        break
                    query["p": p]
                    self.scraperesults(self.request(domain + "/find.php", query))

    def scrapepage(self, page):
        print 222
        subs = re.findall('<div class="altsonsez1(.+?)</div>\s+?</div>\s+?<div>', page, re.DOTALL)
        for s in subs:
            print 9999999999
            r_name = re.search('<a itemprop="url" class="underline".+?href="(.+?)".+?<strong>(.+?)<\/strong>', s)
            link = r_name.group(1)
            name = r_name.group(2)
            r_desc = re.search('<div class="alcd">(.+?)<\/div>', s, re.DOTALL)
            desc = striphtml(r_desc.group(1))
            r_tran = re.search('<div class="alcevirmen">(.+?)<\/div>', s, re.DOTALL)
            tran = striphtml(r_tran.group(1))
            r_rel = re.search('<div class="alrelease">(.+?)<\/div>', s, re.DOTALL)
            rel = striphtml(r_rel.group(1))
            r_iso = re.search('<span class="flag([a-z]{2})">', s)
            iso = r_iso.group(1)
            namestr = "%s, %s, %s, %s" % (name, desc, rel, tran)
            sub = self.sub(namestr, iso)
            sub.download(link)
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
        print link
        paths = link.split("/")
        paths.insert(-1, "download-subtitle")
        link = "/".join(paths)
        remfile = self.request(link, None, None, domain, True)
        fname = remfile.info().getheader("Content-Disposition")
        print fname
        fname = re.search('filename=(.*)', fname)
        print fname
        fname = fname.group(1)
        fname = os.path.join(self.path, fname)
        with open(fname, "wb") as f:
            f.write(remfile.read())
        self.addfile(fname)
