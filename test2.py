import csv
import json
from ast import literal_eval

# csvi = open('NfN_Fsu.csv', 'r', encoding="utf-8")
# csvInputFileReader = csv.DictReader(csvi, dialect='excel')
# for row in csvInputFileReader:
#     print(row['filename'])

file = open('emigrant/5637a1a03262330003ce1c00.json')
jf = json.load(file)
print(jf)
for fs in jf["subjects"]:
    print(fs)


