from pathlib import Path
import re
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset

site = Path(__file__).resolve().parents[1]
fonts = site / 'public/fonts'
stylesheet = site / 'src/styles/fonts.css'

def unicode_ranges(values):
    values = sorted(values)
    result = []
    first = last = values[0]
    for value in values[1:]:
        if value == last + 1:
            last = value
        else:
            result.append(f'U+{first:X}' + (f'-{last:X}' if first != last else ''))
            first = last = value
    result.append(f'U+{first:X}' + (f'-{last:X}' if first != last else ''))
    return ','.join(result)

def face(filename, weight, style, characters, family='Fraunces'):
    return f"@font-face{{font-family:{family};src:url('/autorelabel-rhcsa-rhce/fonts/{filename}') format('woff2');font-weight:{weight};font-style:{style};font-display:swap;unicode-range:{unicode_ranges(characters)}}}"

rules = []
for style in ['normal', 'italic']:
    original_name = f'fraunces-latin-full-{style}.woff2'
    original = TTFont(fonts / original_name)
    full_characters = set(original.getBestCmap())
    weights = [650] if style == 'normal' else [400, 650]
    boundaries = ['100 649', '651 900'] if style == 'normal' else ['100 399', '401 649', '651 900']
    for boundary in boundaries:
        rules.append(face(original_name, boundary, style, full_characters))
    for weight in weights:
        axes = {'wght': weight, 'WONK': 1}
        if weight == 400:
            axes['SOFT'] = 0
        display = instantiateVariableFont(original, axes, inplace=False)
        options = subset.Options()
        options.layout_features = ['*']
        options.name_IDs = ['*']
        options.name_legacy = True
        options.name_languages = ['*']
        options.recalc_timestamp = False
        selection = subset.Subsetter(options=options)
        characters = set(range(0x20, 0x7F)) | {0xA0, 0xD7} | set(range(0x2010, 0x2028))
        selection.populate(unicodes=sorted(characters))
        selection.subset(display)
        display.flavor = 'woff2'
        display.recalcTimestamp = False
        display_name = f'fraunces-{weight}-latin-{style}.woff2'
        display.save(fonts / display_name)
        display_characters = set(display.getBestCmap())
        rules.append(face(original_name, str(weight), style, full_characters - display_characters))
        rules.append(face(display_name, str(weight), style, display_characters))
        print(display_name, (fonts / display_name).stat().st_size, 'bytes', flush=True)
        if weight == 650:
            headline = instantiateVariableFont(display, {'opsz': 80, 'SOFT': 25}, inplace=False)
            headline.flavor = 'woff2'
            headline.recalcTimestamp = False
            headline_name = f'fraunces-headline-{style}.woff2'
            headline.save(fonts / headline_name)
            rules.append(face(headline_name, '650', style, display_characters, '"Fraunces Headline"'))
            print(headline_name, (fonts / headline_name).stat().st_size, 'bytes', flush=True)

other_faces = re.sub(r'@font-face\{font-family:(?:Fraunces|"Fraunces Headline");[^}]*\}\s*', '', stylesheet.read_text())
stylesheet.write_text(other_faces.rstrip() + '\n\n' + '\n\n'.join(rules) + '\n')
