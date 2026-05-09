from pathlib import Path
import csv

p = Path(__file__).parent / 'date_runhash_map.csv'
text = p.read_text(encoding='utf-8')
# Normalize newlines
text = text.replace('\r\n', '\n')
lines = text.split('\n')
# Remove any stray tool wrapper prefixes
clean_lines = []
removed = 0
for l in lines:
    if l.strip().startswith('Result:'):
        removed += 1
        continue
    if l.strip() == '':
        continue
    clean_lines.append(l.rstrip('\r'))

# Ensure header
if not clean_lines:
    print('No data found')
    raise SystemExit(1)
header = clean_lines[0]
if header.lower().strip() != 'date,runhash':
    # try to find header
    for i, l in enumerate(clean_lines[:5]):
        if l.lower().strip() == 'date,runhash':
            clean_lines = clean_lines[i:]
            break

out_lines = [ 'date,runhash' ]
processed = 0
for l in clean_lines[1:]:
    # split on first comma only
    if ',' not in l:
        continue
    date, rest = l.split(',', 1)
    date = date.strip()
    runhash = rest.strip().strip('"')
    # remove any stray surrounding text like 'Result: "..."' if present
    if runhash.startswith('Result:'):
        runhash = runhash.split('Result:',1)[1].strip().strip('"')
    out_lines.append(f'{date},"{runhash}"')
    processed += 1

p.write_text('\n'.join(out_lines) + '\n', encoding='utf-8')
print(f'Wrote {processed} rows, removed {removed} stray lines')
