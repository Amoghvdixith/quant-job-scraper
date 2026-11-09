import requests, re, time
from bs4 import BeautifulSoup
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
s = requests.Session(); s.headers.update({"User-Agent": UA, "Accept-Language":"en-GB,en;q=0.9", "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
for u in ["https://findajob.dwp.gov.uk/search?q=analyst&pp=50&f=3&sb=date&sd=down","https://findajob.dwp.gov.uk/"]:
    t=time.time()
    try:
        r = s.get(u, timeout=90); print("FAJ", r.status_code, len(r.text), round(time.time()-t))
        soup=BeautifulSoup(r.text,"html.parser")
        res = soup.select(".search-result")
        print("results", len(res)); 
        for x in res[:2]: print(x.prettify()[:2500])
        if not res: print(r.text[:1500])
    except Exception as e: print("FAJ ERR", e, round(time.time()-t))
r = s.get("https://www.civilservicejobs.service.gov.uk/csr/index.cgi", timeout=30)
soup=BeautifulSoup(r.text,"html.parser")
for t in soup(["style","svg"]): t.decompose()
print("CSJ", r.status_code, r.headers.get("server"), dict(list(r.headers.items())[:15]))
print(str(soup)[:3000])
import xml.etree.ElementTree as ET
for params in [{"keyword":"analyst"},{"keyword":"analyst","page":2},{"keyword":"analyst","sort":"publicationDateDesc"},{"keyword":"graduate","page":1}]:
    r = s.get("https://www.jobs.nhs.uk/api/v1/search_xml", params=params, timeout=30)
    root = ET.fromstring(r.content)
    v = root.findall("vacancyDetails")
    print("NHS", params, r.status_code, len(v), [x.findtext("postDate")[:10] for x in v][:30], [c.tag for c in root if c.tag!="vacancyDetails"], {c.tag:c.text for c in root if c.tag!="vacancyDetails"})
