import domainconnectzone
#import GDTest
#GDTest.run()

dc = domainconnectzone.DomainConnect("exampleservice.domainconnect.org", "aweber.com.email_auth")


zone_records =[
    #{"type": "SPFM","host": "@","spfRules": "_spf.newsletter.com"}
]

domain="davestys.com"

host = ""

params = {"dkimtxt": "aweber_key_a._domainkey"}


results = dc.apply_template(zone_records, domain, host, params)

for record in results[0]:
  print (record)
