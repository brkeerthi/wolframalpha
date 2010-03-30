#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import urllib2

from lxml.html import document_fromstring, tostring

__version__ = '0.1.0'

    
class TextTable(object):
    def __init__(self, text):
        self.plaintext = text
        self.formated = None
        if not self._preformat():
            self._format()

    def _center(self, s, l):
        """Center a string s in a space of l characters.
           center("foo",5) -> " foo " and so on"""
        d = l-len(s)
        a,b = divmod(d,2)
        return '%s%s%s' % (a*' ', s, (a+b)*' ')
        
    def _preformat(self):
        #Handle multiple calendars
        if 'Su | Mo | Tu | We | Th | Fr | Sa' in self.plaintext:
            cals = self.plaintext.split('Su | Mo | Tu | We | Th | Fr | Sa')
            ret = []
            for cal in cals:
                table = [row.split('|') for row in cal.strip('\n').split('\n')]
                month = None
                if len(table[-1]) > 7:
                    month = table[-1][7]
                    table[-1] = table[-1][:7]
                    
                ret.append('\n'.join('|'.join(row) for row in table))
                if month:
                    ret.append(month.strip())
            self._format('\n'.join(ret))
            return True
                

    def _format(self, text=None):
        if not text:
            text = self.plaintext
        if not '\n' in text:
            self.formated = text
            return
        
        lines = text.split('\n')
        if '|' in lines[0]:
            columns = len(lines[0].split('|'))
        else:
            columns = len(lines[1].split('|'))
            
        table = [[col.strip() for col in line.split('|', columns-1)] for line in lines]

        try:
            lens = [max(len(row[col]) for row in table if len(row) > 1)+2 for col in range(columns)]
        except IndexError:
            return
        
        ret = []
        if len(table[0]) == 1:
            ret.append('┌%s┐' % ('─'*(sum(lens) + columns-1)))
        else:
            ret.append('┌%s┐' % '┬'.join(l*'─' for l in lens)) 
        for ri, row in enumerate(table):
            if len(row) == 1:
                ret.append('│%s│' % self._center(row[0], sum(lens) + columns-1))
                ret.append('├%s┤' % '┬'.join(l*'─' for l in lens))            
            else:
                ret.append('│%s│' % '│'.join(self._center(e,lens[i]) for i,e in enumerate(row)))
            if ri+1 < len(table) and len(table[ri+1]) == 1:
                ret.append('├%s┤' % '┴'.join(l*'─' for l in lens))
        ret.append('└%s┘' % '┴'.join(l*'─' for l in lens)) 
                
        self.formated = '\n'.join(ret)


    
class WolframAlphaResult(object):
    def __init__(self, title, result, result_raw):
        self.title = title
        self.result = result
        self.result_raw = result_raw
        
    def __repr__(self):
        return '<WolframAlphaResult/%r>' % self.title
        

class WolframAlpha(object):
    baseurl = 'http://www88.wolframalpha.com/input/'

    def __init__(self, query, all=True):
        self.query = query
        self.results = []
        self.all = all
        self.update()
    
    def update(self):
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.2) Gecko/2008091620 Firefox/3.0.2'),
                           ('Connection', 'Keep-Alive'),
                           ('Content-Type', 'application/x-www-form-urlencoded')]
        data = opener.open(self.baseurl+"?i="+urllib2.quote(self.query.encode('utf-8'))+"&asynchronous=%s&equal=Submit" % ('pod' if self.all else 'false')).read()
        data = data.replace('</body>', '').replace('</html>', '')
        if self.all:
            recalcurl = re.search("'(recalculate.jsp\?id=[^']*?)'", data, re.I)
            if recalcurl:
                recalcdata = opener.open(self.baseurl+recalcurl.group(1)).read()
            else:
                recalcdata = ""
            podurls = re.findall("'(pod.jsp\?id=[^']*?)'", data+recalcdata, re.I)
            if podurls:
                for url in podurls:
                    try:
                        poddata = str(opener.open(self.baseurl+str(url)).read())
                        data=data+poddata
                    except urllib2.HTTPError:
                        pass
        
        data = data + '</body></html>'
        data = document_fromstring(data)
        pods = data.cssselect('div.pod')
        for pod in pods:
            title = pod.cssselect('h2')
            if len(title) > 0:
                title = title[0].text_content()[:-1]
                text_raw = pod.cssselect('img')[0].get('alt')
                text = text_raw.replace("\\n","\n").replace("\\'s","'s")
                text = re.split(r'\n{2,}',text)
                output = []
                for p in text:
                    p = re.sub(r'(?im)(\n|^)\([^\n]+\)($|\n)', '', p)
                    p = re.sub(r'^\n+', '', p)
                    p = re.sub(r'\n+$', '', p)
                    if p:
                        f = TextTable(p)
                        output.append(f.formated or p)
                if output:
                    text = '\n'.join(output)
                    self.results.append(WolframAlphaResult(title, text, text_raw))
            
            
if __name__ == "__main__":
    w = WolframAlpha("ibm apl", True)
    from pprint import pprint
    pprint(w.results)
    for result in w.results:
        print result.title
        print result.result, '\n\n'