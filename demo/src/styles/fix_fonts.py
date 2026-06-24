import re
with open("main.css", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace('Arial, sans-serif', '"VT323", monospace')
content = content.replace('"Arial Black", Arial, sans-serif', '"Press Start 2P", monospace')
content = content.replace('"Arial Black", Arial, sans-serif', '"Press Start 2P", monospace')

                           
content = content.replace('font-size: 11px;', 'font-size: 16px;')
content = content.replace('font-size: 12px;', 'font-size: 18px;')
content = content.replace('font-size: 13px;', 'font-size: 20px;')
content = content.replace('font-size: 14px;', 'font-size: 22px;')

with open("main.css", "w", encoding="utf-8") as f:
    f.write(content)
