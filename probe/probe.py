import requests, re, sys
from bs4 import BeautifulSoup
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
s = requests.Session(); s.headers["User-Agent"] = UA; s.headers["Accept-Language"]="en-GB,en;q=0.9"
def show(name, r, n=6000):
    print(f"\n\n######## {name} {r.status_code} {r.url} len={len(r.text)}")
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script","style","svg","head"]): t.decompose()
    body = soup.find("main") or soup.body or soup
    print(str(body)[:n])
for name,u in [
 ("FAJ html","https://findajob.dwp.gov.uk/search?q=analyst&pp=50&f=3&sb=date&sd=down"),
 ("FAJ rss","https://findajob.dwp.gov.uk/search.rss?q=analyst&f=3"),
 ("NHS html","https://www.jobs.nhs.uk/candidate/search/results?keyword=finance%20analyst&sort=publicationDateDesc"),
 ("NHS xml","https://www.jobs.nhs.uk/api/v1/search_xml?keyword=finance%20analyst"),
 ("CSC","https://www.civil-service-careers.gov.uk/"),
 ("GRS","https://www.gov.uk/government/organisations/government-recruitment-service"),
]:
    try:
        r = s.get(u, timeout=30)
        if "rss" in name or "xml" in name: print(f"\n\n######## {name} {r.status_code} len={len(r.text)}\n"+r.text[:4000])
        else: show(name, r)
    except Exception as e: print(name, "ERR", e)
# Civil Service Jobs
r = s.get("https://www.civilservicejobs.service.gov.uk/csr/index.cgi", timeout=30)
print(f"\n\n######## CSJ home {r.status_code} {r.url}")
soup = BeautifulSoup(r.text, "html.parser")
for f in soup.find_all("form"):
    print("FORM", f.get("action"), f.get("method"), f.get("id"))
    for i in f.find_all(["input","select"]):
        print("  ", i.name, i.get("name"), i.get("type"), (i.get("value") or "")[:80])
